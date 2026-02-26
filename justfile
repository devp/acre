default: typecheck lintfix test

typecheck:
  PYTHONPATH=src uv run pyright

lintfix:
  uv run ruff check --fix

test:
  PYTHONPATH=src uv run pytest
