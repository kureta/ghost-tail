.PHONY: init

init:
	poetry install --with dev
	poetry run pre-commit install
	poetry run dvc pull
