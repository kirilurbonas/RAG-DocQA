"""Tests for team management routes."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Base
from app.db.database import get_db
from app.services.user_service import UserService


@pytest.fixture
def db_session():
    """Create in-memory SQLite database."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def client(db_session):
    """FastAPI test client with in-memory database."""
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


@pytest.fixture
def auth_token(client, db_session):
    """Create a user and return auth token."""
    user_service = UserService(db_session)
    user_service.create_user(
        email="user@example.com",
        username="testuser",
        password="Password123"
    )

    response = client.post("/api/v1/auth/login", json={
        "email": "user@example.com",
        "password": "Password123"
    })

    return response.json()["access_token"]


class TestTeamCreation:
    """Test team creation."""

    def test_create_team_success(self, client, auth_token):
        """Test successful team creation."""
        response = client.post(
            "/api/v1/teams",
            json={"name": "Engineering Team"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering Team"
        assert data["owner_id"]
        assert data["id"]

    def test_create_team_empty_name(self, client, auth_token):
        """Test team creation with empty name."""
        response = client.post(
            "/api/v1/teams",
            json={"name": ""},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 422  # Validation error

    def test_create_team_no_auth(self, client):
        """Test team creation without authentication."""
        response = client.post(
            "/api/v1/teams",
            json={"name": "Engineering Team"}
        )

        assert response.status_code in [401, 403]


class TestTeamRetrieval:
    """Test retrieving teams."""

    def test_get_user_teams(self, client, auth_token, db_session):
        """Test getting user's teams."""
        # Create a team
        user_service = UserService(db_session)
        user = user_service.authenticate_user("user@example.com", "Password123")
        team = user_service.create_team(user['id'], "Test Team")

        # Get teams
        response = client.get(
            "/api/v1/teams",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Team"

    def test_get_teams_empty(self, client, auth_token):
        """Test getting teams when user has none."""
        response = client.get(
            "/api/v1/teams",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0

    def test_get_teams_no_auth(self, client):
        """Test getting teams without authentication."""
        response = client.get("/api/v1/teams")

        assert response.status_code in [401, 403]


class TestTeamMembers:
    """Test team member management."""

    def test_add_team_member(self, client, auth_token, db_session):
        """Test adding a team member."""
        # Create users
        user_service = UserService(db_session)
        user1 = user_service.authenticate_user("user@example.com", "Password123")
        user2 = user_service.create_user(
            email="user2@example.com",
            username="user2",
            password="Password123"
        )

        # Create team
        team = user_service.create_team(user1['id'], "Test Team")

        # Add member
        response = client.post(
            f"/api/v1/teams/{team['id']}/members",
            json={"user_id": user2['id'], "role": "member"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        assert "Member added successfully" in response.json()["message"]

    def test_add_team_member_no_auth(self, client, db_session):
        """Test adding team member without authentication."""
        user_service = UserService(db_session)
        user = user_service.create_user(
            email="user@example.com",
            username="testuser",
            password="Password123"
        )
        team = user_service.create_team(user['id'], "Test Team")

        response = client.post(
            f"/api/v1/teams/{team['id']}/members",
            json={"user_id": "some-user-id", "role": "member"}
        )

        assert response.status_code in [401, 403]
