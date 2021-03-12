from django.db import IntegrityError
from django.core.paginator import InvalidPage, Paginator
from django.http import Http404
from django.core.exceptions import FieldError, ValidationError, MultipleObjectsReturned

from django.http.request import validate_host
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin
from django.conf import settings

from my_site.restful.response import (
    APIResponse,
    ErrorAPIResponse,
    CollectionAPIResponse,
    OperationAPIResponse,
)

import json


class APIViewSet(SingleObjectMixin, View):
    """
    Intentionally simple parent class for all API views.
    """

    # View
    model = None
    queryset = None
    http_method_names = [
        "head",
        "options",
        "get",
        "post",
        "patch",
        "put",
        "delete",
    ]

    # SingleObjectMixin
    pk_url_kwarg = "pk"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"
    query_pk_and_slug = False

    # MultipleObjectMixin
    allow_empty = True
    paginate_by = 100
    paginate_orphans = 0
    paginator_class = Paginator
    page_kwarg = "page"
    ordering = "pk"

    # ContextMixin
    context_object_name = "result"
    extra_context = None

    # APIViewSetMixin
    actions = None

    # CORSMixin
    cors_allowed_origins = tuple(settings.ALLOWED_HOSTS)
    cors_blocked_origins = tuple([])

    def corsable(self, response, request):
        """The Cross-Origin Resource Sharing request support handler"""

        # Indicates where a fetch originates from.
        origin = request.headers.get("Origin")

        if (origin is not None) and (
            validate_host(origin, self.cors_allowed_origins)
            and not validate_host(origin, self.cors_blocked_origins)
        ):
            # Indicates whether the response can be shared.
            response["Access-Control-Allow-Origin"] = origin
            # Indicates whether or not the response to the request can be exposed when the credentials flag is true.
            response["Access-Control-Allow-Credentials"] = "true"
            # Indicates which headers can be exposed as part of the response by listing their names.
            response["Access-Control-Expose-Headers"] = "true"

            # Unlike `Simple Requests`, for `Preflighted Requests` the browser first sends an HTTP request
            #   using the OPTIONS method to the resource on the other origin,
            #   in order to determine if the actual request is safe to send.
            if request.method == "OPTIONS":
                # Indicates how long the results of a preflight request can be cached.
                response["Access-Control-Max-Age"] = "3600"

                # Used when issuing a preflight request to let the server know
                #   which HTTP headers will be used when the actual request is made.
                request_method = request.headers.get(
                    "Access-Control-Request-Method", ""
                )
                # Specifies the method or methods allowed
                #   when accessing the resource in response to a preflight request.
                response["Access-Control-Allow-Methods"] = request_method
                # Used when issuing a preflight request to let the server know
                #   which HTTP method will be used when the actual request is made.
                request_headers = request.headers.get(
                    "Access-Control-Request-Headers", ""
                )
                # Used in response to a preflight request to indicate
                #   which HTTP headers can be used when making the actual request.
                response["Access-Control-Allow-Headers"] = request_headers

            # To indicate to clients that server responses will differ based on the value of the Origin request header.
            response["Vary"] = "Origin"

    def setup(self, request, *args, **kwargs):
        """Initialize attributes shared by all view methods."""

        # Bind methods to actions
        actions = self.actions or {}
        for method, action in actions.items():
            handler = getattr(self, action)
            setattr(self, method, handler)

        return super().setup(request, *args, **kwargs)

    def get_context_data(self, data):
        """Insert the result into the context dict."""

        context = {self.context_object_name: data}

        if self.extra_context is not None:
            context.update(self.extra_context)
        return context

    @classmethod
    def get_verbose_name(cls):
        """A human-readable name for the object, singular."""

        return cls.model._meta.verbose_name

    @classmethod
    def get_verbose_name_plural(cls):
        """The plural name for the object."""

        return cls.model._meta.verbose_name_plural

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        """Try to dispatch to the right method."""

        try:
            response = super().dispatch(request, *args, **kwargs)
        except Http404:
            response = ErrorAPIResponse("100100")
            response.status_code = 404
        except MultipleObjectsReturned:
            response = ErrorAPIResponse("100101")
        except IntegrityError:
            response = ErrorAPIResponse("100102")
        except FieldError:
            response = ErrorAPIResponse("100103")
        except (ValueError, AttributeError):
            response = ErrorAPIResponse("100104")
        except ValidationError:
            response = ErrorAPIResponse("100105")
        except InvalidPage:
            response = ErrorAPIResponse("100300")

        self.corsable(response, request)
        return response

    def head(self, request, *args, **kwargs):
        """Return metadata of the result for a GET response."""

        response = self.get(self, request, *args, **kwargs)
        if not response.streaming and not response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))
        response.content = ""
        return response

    def options(self, request, *args, **kwargs):
        """Get information about a request."""

        return super().options(self, request, *args, **kwargs)

    def fetch_detail(self, request, *args, **kwargs):
        """Return the current value of an object."""

        target_object = self.get_object()
        context = self.get_context_data(target_object)
        return APIResponse(context)

    def fetch_list(self, request, *args, **kwargs):
        """Return the current paginated collection value of multiple objects."""

        order_by = request.GET.get("order_by") or self.ordering
        page_size = request.GET.get("size") or self.paginate_by
        page_number = (
            self.kwargs.get(self.page_kwarg)
            or self.request.GET.get(self.page_kwarg)
            or 1
        )

        queryset = self.get_queryset().exclude(is_deleted=True)
        filtered_queryset = queryset.filter(**kwargs)
        ordered_queryset = filtered_queryset.order_by(order_by)
        paginator = self.paginator_class(
            ordered_queryset,
            page_size,
            orphans=self.paginate_orphans,
            allow_empty_first_page=self.allow_empty,
        )
        page = paginator.page(page_number)
        context = self.get_context_data(page.object_list)
        return CollectionAPIResponse(context, formatter_params={"page": page})

    def create(self, request, *args, **kwargs):
        """Create a new object based on the data provided, or submit a command."""

        data = json.loads(request.body)
        new_object = self.model.objects.create(**kwargs)

        try:
            new_object.update(**data)
        except Exception as error:
            new_object.refresh_from_db()
            new_object.delete()
            raise error

        context = self.get_context_data(new_object)
        return OperationAPIResponse(context)

    def update(self, request, *args, **kwargs):
        """Apply a partial update to an object."""

        data = json.loads(request.body)
        target_object = self.get_object()
        target_object.update(**data)
        context = self.get_context_data(target_object)
        return OperationAPIResponse(context)

    def update_or_create(self, request, *args, **kwargs):
        """Replace an object, or create a named object, when applicable."""

        data = json.loads(request.body)

        created = False
        try:
            target_object = self.get_object()
        except Http404:
            target_object = self.model.objects.create(**kwargs)
            created = True

        try:
            target_object.update(**data)
        except Exception as error:
            if created:
                target_object.refresh_from_db()
                target_object.delete()
            raise error

        context = self.get_context_data(target_object)
        return OperationAPIResponse(context)

    def drop(self, request, *args, **kwargs):
        """Delete an object."""

        target_object = self.get_object()
        target_object.delete()
        context = self.get_context_data(target_object)
        return OperationAPIResponse(context)
