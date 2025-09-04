default:
  poetry run pyright
  poetry run ruff check --fix
  poetry run pytest
