from rest_framework.pagination import PageNumberPagination


class DefaultPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


_TRUTHY = ("1", "true", "yes")


class AllowUnpaginatedMixin:
    """Let a list endpoint return every row when called with ``?all=true``.

    Pickers need the whole set, not a page. With ``page_size`` at 15 a plain
    list request silently truncates — a hall picker showed 15 of 67 halls and a
    class picker 15 of 247, with no indication anything was missing. Callers
    that render a dropdown pass ``?all=true``; the response is then a plain
    array rather than the paginated envelope.
    """

    def paginate_queryset(self, queryset):
        all_param = self.request.query_params.get("all")
        if all_param and all_param.lower() in _TRUTHY:
            return None
        return super().paginate_queryset(queryset)
