# path: tests/test_production_stack_files.py
"""Tests that assert tracked production stack files expose key wiring."""

from __future__ import annotations

from pathlib import Path


def test_production_compose_contains_required_services() -> None:
    """The production compose file should define the expected core services."""
    compose_text = Path("docker-compose.prod.yml").read_text()

    assert "db:" in compose_text
    assert "web:" in compose_text
    assert "nginx:" in compose_text
    assert "dockerfile: Dockerfile" in compose_text
    assert "service_healthy" in compose_text


def test_nginx_site_config_exposes_static_media_and_health() -> None:
    """The Nginx site config should proxy app traffic and expose the health path."""
    nginx_site = Path("infra/nginx/default.conf").read_text()

    assert "location /static/" in nginx_site
    assert "location /media/" in nginx_site
    assert "location = /api/health/" in nginx_site
    assert "proxy_pass http://returnhub_app;" in nginx_site


def test_deployment_doc_mentions_build_and_health_verification() -> None:
    """Deployment documentation should include the critical operator steps."""
    deployment_doc = Path("docs/DEPLOYMENT.md").read_text()

    assert "docker compose -f docker-compose.prod.yml --env-file .env.prod build" in deployment_doc
    assert "curl -i http://127.0.0.1/api/health/" in deployment_doc
