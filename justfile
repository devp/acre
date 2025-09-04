default:
  poetry run pyright
  poetry run ruff check --fix
