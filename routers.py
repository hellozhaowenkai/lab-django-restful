from django.urls import path, re_path, include


class APIRouter:
    """
    The RESTful style API Router.
    """

    list_actions = {
        "get": "fetch_list",
        "post": "create",
    }
    detail_actions = {
        "get": "fetch_detail",
        "put": "update_or_create",
        "patch": "update",
        "delete": "drop",
    }

    def __init__(self, view_set):
        self.view_set = view_set
        self.verbose_name = view_set.get_verbose_name()
        self.verbose_name_plural = view_set.get_verbose_name_plural()
        self.patterns = []
        self.sub_patterns = []

        self.register("", self.list_actions)
        for rest_key in self.rest_keys:
            self.register(f"{rest_key}/", self.detail_actions)

    @property
    def rest_keys(self):
        return "<int:pk>", "<uuid:uuid>"

    @property
    def sub_rest_keys(self):
        return f"<int:{self.verbose_name}_id>", f"<uuid:{self.verbose_name}__uuid>"

    @property
    def urls(self):
        for sub_rest_key in self.sub_rest_keys:
            self.patterns.append(path(f"{sub_rest_key}/", include(self.sub_patterns)))
        return path(f"{self.verbose_name_plural}/", include(self.patterns))

    def register(self, url, actions):

        self.patterns.append(
            path(
                url,
                self.view_set.as_view(actions=actions),
            )
        )

    def add_sub_routers(self, *sub_routers):
        self.sub_patterns.extend([sub_router.urls for sub_router in sub_routers])
