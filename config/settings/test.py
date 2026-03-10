# path: config/settings/test.py
"""Test settings for ReturnHub."""
from .base import *  # noqa: F403,F401

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
