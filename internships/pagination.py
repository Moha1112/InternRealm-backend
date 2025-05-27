from django.core.paginator import Paginator, EmptyPage

class CustomPagination:
    def __init__(self):
        self.page_size = 20
        self.page_size_query_param = 'page_size'
        self.max_page_size = 100
        self.page_query_param = 'page'
        self.request = None
        self.page = None
        self.paginator = None

    def get_page_size(self, request):
        """Determine the page size, honoring request parameters and max limit"""
        try:
            page_size = int(request.GET.get(self.page_size_query_param, self.page_size))
            return min(max(page_size, 1), self.max_page_size)
        except (ValueError, TypeError):
            return self.page_size

    def paginate_queryset(self, queryset, request):
        """Paginate the queryset and return the page items"""
        self.request = request
        page_size = self.get_page_size(request)

        try:
            page_number = int(request.GET.get(self.page_query_param, 1))
        except (ValueError, TypeError):
            page_number = 1

        self.paginator = Paginator(queryset, page_size)

        try:
            self.page = self.paginator.page(page_number)
            return list(self.page.object_list)
        except EmptyPage:
            return []

    def get_paginated_response(self, data):
        """Return the paginated response structure"""
        if not hasattr(self, 'page') or self.page is None:
            return {
                'success': True,
                'pagination': {
                    'total_items': 0,
                    'total_pages': 0,
                    'current_page': 1,
                    'page_size': self.get_page_size(self.request),
                    'next': None,
                    'previous': None
                },
                'results': data,
                'data': {'filters': {}}
            }

        base_url = self.request.build_absolute_uri().split('?')[0]
        params = self.request.GET.copy()

        next_url = None
        if self.page.has_next():
            params[self.page_query_param] = self.page.next_page_number()
            next_url = f"{base_url}?{params.urlencode()}"

        previous_url = None
        if self.page.has_previous():
            params[self.page_query_param] = self.page.previous_page_number()
            previous_url = f"{base_url}?{params.urlencode()}"

        return {
            'success': True,
            'pagination': {
                'total_items': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'next': next_url,
                'previous': previous_url
            },
            'results': data,
            'data': {}  # This empty dict allows your view to add filters
        }

"""
class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return {
            'success': True,
            'pagination': {
                'total_items': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'current_page': self.page.number,
                'page_size': self.get_page_size(self.request),
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'results': data
        }

    def paginate_queryset(self, queryset, request, view=None):
        try:
            return super().paginate_queryset(queryset, request, view)
        except EmptyPage:
            return []
"""