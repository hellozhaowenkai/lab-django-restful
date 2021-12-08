from django.db import models
from django.http import JsonResponse
from django.core.serializers import serialize
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.timezone import now

from my_site.restful.models import OperationAPIState


class APIEncoder(DjangoJSONEncoder):
    """
    DjangoJSONEncoder subclass that knows how to encode QuerySet and Model.
    """

    def default(self, obj):
        if isinstance(
            obj,
            (
                models.QuerySet,
                models.Model,
            ),
        ):
            return self.jsonable(obj)

        return super().default(obj)

    def jsonable(self, obj):
        """The JavaScript Object Notation format support handler."""

        if isinstance(obj, models.Model):
            iterable = [obj]
            return self.jsonable(iterable)[0]

        return serialize("python", obj)


class APIResponse(JsonResponse):
    """
    An API response class that consumes `any data` to be serialized to JSON.
    """

    def __init__(self, context, formatter_params=None):
        if formatter_params is None:
            formatter_params = {}

        response_content = self.formatter(context, **formatter_params)
        super().__init__(
            data=response_content,
            encoder=APIEncoder,
            safe=True,
            # json_dumps_params={"sort_keys": True},
        )

    def formatter(self, context, **kwargs):
        response_data = context
        return response_data


class ErrorAPIResponse(APIResponse):
    """
    An API response class that consumes `error info data` to be serialized to JSON.
    """

    ERROR_STATUS_CODE = {
        # EXAMPLE
        "100000": "Example: This is an example error message.",
        # DATABASE
        "100100": "NotFound: No target found matching the query.",
        "100101": "MultipleObjectsReturned: The query returned multiple objects when only one was expected.",
        "100102": "IntegrityError: Some kind of problem with a valid index.",
        "100103": "FieldError: Some kind of problem with a model field.",
        "100104": "ValueError: Some fields do not exist in this model or are m2m fields.",
        "100105": "ValidationError: Enter a valid value.",
        # AUTHENTICATION
        "100200": "ValidationError: A user with that username already exists.",
        "100201": "PermissionDenied: The user did not have permission to do that.",
        # PAGINATION
        "100300": "InvalidPage: The requested page is invalid (i.e. not an integer) or contains no objects.",
    }

    def formatter(self, code, message="", **kwargs):
        response_data = {
            # The error object.
            "error": {
                # One of a server-defined set of error codes.
                "code": code,
                # A human-readable representation of the error.
                "message": message or self.ERROR_STATUS_CODE[code],
            }
        }
        return response_data


class CollectionAPIResponse(APIResponse):
    """
    An API response class that consumes `a list of objects data` to be serialized to JSON.
    """

    def formatter(self, context, page=None, **kwargs):
        response_data = {
            # The total number of objects, across all pages.
            "count": page.paginator.count,
            # The maximum number of items to include on a page.
            "per_page": page.paginator.per_page,
            # The total number of pages.
            "num_pages": page.paginator.num_pages,
            # A 1-based range iterator of page numbers, e.g. [1, 2, 3, 4].
            "page_range": [i for i in page.paginator.page_range],
            # The previous page number.
            "previous": page.previous_page_number() if page.has_previous() else 0,
            # The 1-based page number for this page.
            "current": page.number,
            # The next page number.
            "next": page.next_page_number() if page.has_next() else 0,
            # The 1-based index of the first object on the page, relative to all of the objects in the paginator’s list.
            "start_index": page.start_index(),
            # The 1-based index of the last object on the page, relative to all of the objects in the paginator’s list.
            "end_index": page.end_index(),
            # The list of objects on this page.
            **context,
        }
        return response_data


class OperationAPIResponse(APIResponse):
    """
    An API response class that consumes `operation info data` to be serialized to JSON.
    """

    def formatter(
        self,
        context,
        created_at=None,
        last_action_at=None,
        percent_complete=100,
        state=OperationAPIState.SUCCEEDED,
    ):
        response_data = {
            # The datetime when the operation was created.
            "created_at": created_at or now(),
            # The datetime for when the current state was entered.
            "last_action_at": last_action_at or now(),
            # Sometimes it is impossible for services to know with any accuracy when an operation will complete.
            "percent_complete": percent_complete,
            # Operations MUST support the following states: [NOT_STARTED | RUNNING | SUCCEEDED | FAILED].
            "state": state,
            # The result of the operation.
            **context,
        }
        return response_data
