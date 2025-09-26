# tests/conftest.py
import os, sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("JWT_ACCESS_MINUTES", "15")
os.environ.setdefault("JWT_REFRESH_DAYS", "7")

# Utilise ta DB locale; tu peux définir TEST_DATABASE_URL dans .env si tu veux une base dédiée
TEST_DB = os.getenv("TEST_DATABASE_URL", "postgresql+psycopg://app_user:app_password_strong@localhost:5433/app_db_test")

from app import create_app
from app.extensions import db

@pytest.fixture(scope="session")
def app():
    app = create_app()
    # Override pour être sûr d'utiliser la bonne DB
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI=TEST_DB,
        WTF_CSRF_ENABLED=False,
    )
    with app.app_context():
        # tables propres pour la session de tests
        db.drop_all()
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()
