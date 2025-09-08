default: typecheck lintfix test

typecheck:
  poetry run pyright

lintfix:
  poetry run ruff check --fix

test:
  poetry run pytest
