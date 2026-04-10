# path: accounts/forms.py
"""Authentication forms for surface-specific login pages."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm


class SurfaceAuthenticationForm(AuthenticationForm):
    """Bootstrap-friendly authentication form for all ReturnHub surfaces."""

    username = forms.CharField(
        label="Email or username",
        widget=forms.TextInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "name@example.com",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control form-control-lg",
                "placeholder": "Password",
                "autocomplete": "current-password",
            }
        ),
    )
