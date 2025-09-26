SHELL := /usr/bin/bash
.ONESHELL:
.PHONY: run fmt lint db-init db-migrate db-upgrade run-venv

run:
	FLASK_APP=wsgi.py flask run --port 5000

# Variante qui active le venv automatiquement (utile si tu l'oublies)
run-venv:
	. .venv/Scripts/activate; FLASK_APP=wsgi.py flask run --port 5000

fmt:
	python -m pip install -q black && black app wsgi.py

lint:
	python -m pip install -q ruff && ruff check app

db-init:
	FLASK_APP=wsgi.py flask db init

db-migrate:
	FLASK_APP=wsgi.py flask db migrate -m "auto"

db-upgrade:
	FLASK_APP=wsgi.py flask db upgrade
