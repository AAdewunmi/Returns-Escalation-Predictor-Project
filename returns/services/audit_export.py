# path: apps/returns/services/audit_export.py
"""
Audit export helpers for return cases.
"""

from __future__ import annotations

import csv
from io import StringIO

from apps.returns.models import ReturnCase


def build_return_case_audit_csv(return_case: ReturnCase) -> str:
    """
    Build a CSV export containing case metadata, events, and document rows.
    """

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["section", "key", "value"])

    writer.writerow(["case", "reference", return_case.reference])
    writer.writerow(["case", "status", return_case.status])
    writer.writerow(["case", "priority", return_case.priority])

    latest_risk = return_case.risk_scores.first()
    if latest_risk:
        writer.writerow(["risk", "score", latest_risk.score])
        writer.writerow(["risk", "label", latest_risk.label])
        writer.writerow(["risk", "reason_codes", ",".join(latest_risk.reason_codes)])

    for event in return_case.events.all():
        writer.writerow(["event", event.event_type, event.created_at.isoformat()])

    for document in return_case.documents.all():
        writer.writerow(["document", "document_kind", document.document_kind])
        writer.writerow(["document", "original_filename", document.original_filename])
        writer.writerow(["document", "content_type", document.content_type])
        writer.writerow(["document", "size_bytes", document.size_bytes])
        writer.writerow(["document", "checksum_sha256", document.checksum_sha256])

    return output.getvalue()
