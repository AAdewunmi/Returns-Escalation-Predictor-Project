# path: ui/error_views.py
"""Custom error views that preserve the ReturnHub product shell."""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def error_403(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Render the branded forbidden page."""
    return render(request, "errors/403.html", status=403)


def error_404(request: HttpRequest, exception: Exception) -> HttpResponse:
    """Render the branded not-found page."""
    return render(request, "errors/404.html", status=404)


def error_500(request: HttpRequest) -> HttpResponse:
    """Render the branded server-error page."""
    return render(request, "errors/500.html", status=500)
