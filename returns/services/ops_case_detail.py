"""Detail-page context builders for the case workspace."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.base_user import AbstractBaseUser
from django.core.exceptions import PermissionDenied
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404

from returns.models import CaseEvent, EvidenceDocument, ReturnCase
from returns.services.cases import _actor_role
from returns.services.documents import list_documents_for_case


def get_case_detail_case(*, case_id: int) -> ReturnCase:
    """Fetch a case with the related entities needed by the workspace."""

    return get_object_or_404(
        ReturnCase.objects.select_related(
            "customer__user",
            "merchant__user",
            "risk_score",
        ).prefetch_related(
            Prefetch(
                "documents",
                queryset=EvidenceDocument.objects.order_by("-created_at", "-id"),
            ),
            Prefetch(
                "events",
                queryset=CaseEvent.objects.select_related("actor").order_by("-created_at", "-id"),
            ),
        ),
        pk=case_id,
    )


def get_case_detail_actor_role(*, actor: AbstractBaseUser, return_case: ReturnCase) -> str:
    """Resolve the request actor role for the case workspace."""

    actor_role = _actor_role(actor)
    if actor_role in {"admin", "ops"}:
        return actor_role

    if actor_role == "customer" and return_case.customer.user_id == actor.id:
        return actor_role

    if actor_role == "customer":
        raise PermissionDenied("You do not have access to this case.")

    if actor_role == "merchant" and return_case.merchant.user_id == actor.id:
        return actor_role

    if actor_role == "merchant":
        raise PermissionDenied("You do not have access to this case.")

    return ""


def build_ops_case_detail_context(
    *,
    case_id: int,
    actor: AbstractBaseUser | None = None,
) -> dict[str, Any]:
    """Build the shared case workspace context for UI views."""

    return_case = get_case_detail_case(case_id=case_id)
    actor_role = ""
    documents = return_case.documents.order_by("-created_at", "-id")

    if actor is not None and actor.is_authenticated:
        actor_role = get_case_detail_actor_role(actor=actor, return_case=return_case)
        try:
            documents = list_documents_for_case(return_case=return_case, actor=actor).order_by(
                "-created_at",
                "-id",
            )
        except PermissionDenied:
            documents = return_case.documents.none()

    return {
        "return_case": return_case,
        "documents": documents,
        "events": return_case.events.order_by("-created_at", "-id"),
        "latest_risk": getattr(return_case, "risk_score", None),
        "actor_role": actor_role,
        "page_title": f"Case {return_case.order_reference}",
    }
