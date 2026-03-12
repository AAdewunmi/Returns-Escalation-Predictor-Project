# path: common/templatetags/querystring.py
"""Template tags for query-string preservation."""
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def replace_query(context, **kwargs) -> str:
    """Replace or remove query-string values while preserving all others."""
    request = context["request"]
    query = request.GET.copy()

    for key, value in kwargs.items():
        if value is None:
            query.pop(key, None)
            continue
        query[key] = value

    return query.urlencode()
