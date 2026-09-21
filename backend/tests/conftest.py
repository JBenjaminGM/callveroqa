"""
Configuración compartida de los tests.

Usa una base de datos SQLite en memoria y sustituye la dependencia get_db
para no necesitar PostgreSQL durante los tests.
"""

import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import get_db
from app.limiter import limiter
from app.main import app
from app.models import Agent, Base, User
from app.models.user import ROLE_ASESOR
from app.utils.security import hash_password

# Almacenamiento de audios en una carpeta temporal durante los tests.
settings.storage_path = tempfile.mkdtemp(prefix="callveroqa_test_")

# Se desactiva el rate limiting en los tests: el cliente de pruebas usa
# siempre la misma IP y dispararía el límite de /auth/login entre tests.
limiter.enabled = False

# Motor SQLite en memoria, compartido entre conexiones (StaticPool).
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def _setup_database():
    """Crea las tablas antes de cada test y las elimina al terminar."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Entrega una sesión de base de datos para usar en los tests."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _override_get_db():
    """Versión de get_db que usa la base de datos de tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Cliente HTTP de pruebas con la dependencia de BD sustituida."""
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    """Crea un usuario administrador de prueba."""
    user = User(
        email="admin@test.com",
        password_hash=hash_password("Admin123!"),
        name="Admin Test",
        role="admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_agent(db_session):
    """Crea un ejecutivo de prueba (para vincular a un asesor)."""
    agent = Agent(name="Asesor Demo", email="asesor.agent@test.com", campaign="Tarjetas")
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


@pytest.fixture
def asesor_user(db_session, sample_agent):
    """Crea un usuario con rol asesor vinculado a `sample_agent`."""
    user = User(
        email="asesor@test.com",
        password_hash=hash_password("Asesor123!"),
        name="Asesor Demo",
        role=ROLE_ASESOR,
        agent_id=sample_agent.id,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def asesor_headers(client, asesor_user):
    """Cabeceras Authorization con un token válido del asesor."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "asesor@test.com", "password": "Asesor123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(client, admin_user):
    """Devuelve las cabeceras Authorization con un token válido del admin."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "Admin123!"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
