
```markdown
<!-- path: docs/DEMO_SCRIPT.md -->
# ReturnHub Demo Script

## Goal

This script provides a deterministic walkthrough of the full multi-surface ReturnHub product after Sprint 7. It is written for a five to eight minute demo and uses the seeded environment created in earlier sprints.

## Pre-demo preparation

```bash
python manage.py migrate
python manage.py seed_demo
pytest -q
python manage.py runserver