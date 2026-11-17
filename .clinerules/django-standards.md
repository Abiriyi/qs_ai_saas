# Django Project Standards

These rules apply to every task in this Django project.

## Virtual Environment

- Always activate or target this project's local virtual environment (`.venv`).
- Local environment reference: `ubuntu@ubuntu-vm:~/projects/qs_ai_saas`.


## File Boundaries

- Never inspect, import from, or modify files outside this project's root directory.

## Testing

- Run tests using `pytest` (or `python manage.py test`) before concluding any code modification task.

## Database Migrations

- Never run `makemigrations` or `migrate` on production databases without explicit confirmation.

## Code Style & Architecture

- Follow PEP 8.
- Use type hints for all new functions.
- Keep business logic in `services.py` rather than views or serializers.

## Django ORM Best Practices

- Use Django ORM best practices (`select_related`, `prefetch_related`) to prevent N+1 query issues.
