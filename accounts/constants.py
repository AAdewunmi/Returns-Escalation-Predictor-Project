# path: accounts/constants.py
"""Role, group, and surface constants for ReturnHub."""

ROLE_ADMIN = "admin"
ROLE_OPS = "ops"
ROLE_CUSTOMER = "customer"
ROLE_MERCHANT = "merchant"

PRIMARY_ROLE_ORDER = (
    ROLE_ADMIN,
    ROLE_OPS,
    ROLE_CUSTOMER,
    ROLE_MERCHANT,
)

GROUP_NAMES = {
    ROLE_ADMIN: "admin",
    ROLE_OPS: "ops",
    ROLE_CUSTOMER: "customer",
    ROLE_MERCHANT: "merchant",
}

SURFACE_LOGIN_ROUTE_NAMES = {
    ROLE_ADMIN: "accounts:login_admin",
    ROLE_OPS: "accounts:login_ops",
    ROLE_CUSTOMER: "accounts:login_customer",
    ROLE_MERCHANT: "accounts:login_merchant",
}

SURFACE_CONSOLE_ROUTE_NAMES = {
    ROLE_ADMIN: "accounts:console_admin",
    ROLE_OPS: "accounts:console_ops",
    ROLE_CUSTOMER: "accounts:console_customer",
    ROLE_MERCHANT: "accounts:console_merchant",
}

SURFACE_ALLOWED_PREFIXES = {
    ROLE_ADMIN: ("/admin/", "/console/admin/"),
    ROLE_OPS: ("/ops/", "/console/ops/"),
    ROLE_CUSTOMER: ("/customer/", "/console/customer/"),
    ROLE_MERCHANT: ("/merchant/", "/console/merchant/"),
}
