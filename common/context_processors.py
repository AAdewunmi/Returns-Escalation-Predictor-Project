# path: common/context_processors.py
"""Context processors shared across the product shell."""


def app_shell(request) -> dict:
    """Expose lightweight shell metadata to templates."""
    active_role_groups = []
    if request.user.is_authenticated:
        active_role_groups = list(
            request.user.groups.order_by("name").values_list("name", flat=True)
        )

    return {
        "brand_name": "ReturnHub",
        "active_role_groups": active_role_groups,
        "current_path": request.path,
    }
