default: lintfix typecheck test

pre-push: lintcheck typecheck test

typecheck:
  PYTHONPATH=src uv run pyright

lintcheck:
  uv run ruff check

lintfix:
  uv run ruff check --fix

test:
  PYTHONPATH=src uv run pytest
