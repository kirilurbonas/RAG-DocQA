"""Tests for authentication routes."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Base, User
from app.db.database import get_db


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


class TestAuthRegistration:
    """Test user registration."""

    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post("/api/v1/auth/register", json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePass123"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["access_token"]
        assert data["token_type"] == "bearer"
        assert data["email"] == "newuser@example.com"
        assert data["username"] == "newuser"

    def test_register_duplicate_email(self, client, db_session):
        """Test registration with duplicate email."""
        # Create first user
        from app.services.user_service import UserService
        user_service = UserService(db_session)
        user_service.create_user(
            email="existing@example.com",
            username="user1",
            password="Password123"
        )

        # Try to register with same email
        response = client.post("/api/v1/auth/register", json={
            "email": "existing@example.com",
            "username": "user2",
            "password": "Password123"
        })

        assert response.status_code == 400
        assert "already in use" in response.json()["detail"]

    def test_register_invalid_email(self, client):
        """Test registration with invalid email."""
        response = client.post("/api/v1/auth/register", json={
            "email": "not-an-email",
            "username": "user",
            "password": "Password123"
        })

        assert response.status_code == 422  # Validation error

    def test_register_short_password(self, client):
        """Test registration with short password."""
        response = client.post("/api/v1/auth/register", json={
            "email": "user@example.com",
            "username": "user",
            "password": "short"
        })

        assert response.status_code == 400

    def test_register_short_username(self, client):
        """Test registration with short username."""
        response = client.post("/api/v1/auth/register", json={
            "email": "user@example.com",
            "username": "ab",
            "password": "Password123"
        })

        assert response.status_code == 422


class TestAuthLogin:
    """Test user login."""

    def test_login_success(self, client, db_session):
        """Test successful login."""
        from app.services.user_service import UserService
        user_service = UserService(db_session)
        user_service.create_user(
            email="user@example.com",
            username="testuser",
            password="TestPassword123"
        )

        response = client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "TestPassword123"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["access_token"]
        assert data["email"] == "user@example.com"

    def test_login_wrong_password(self, client, db_session):
        """Test login with wrong password."""
        from app.services.user_service import UserService
        user_service = UserService(db_session)
        user_service.create_user(
            email="user@example.com",
            username="testuser",
            password="CorrectPassword123"
        )

        response = client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "WrongPassword123"
        })

        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        """Test login for nonexistent user."""
        response = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "Password123"
        })

        assert response.status_code == 401


class TestChangePassword:
    """Test password change."""

    def test_change_password_success(self, client, db_session):
        """Test successful password change."""
        from app.services.user_service import UserService
        user_service = UserService(db_session)
        user = user_service.create_user(
            email="user@example.com",
            username="testuser",
            password="OldPassword123"
        )

        # Login to get token
        login_response = client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "OldPassword123"
        })
        token = login_response.json()["access_token"]

        # Change password
        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "OldPassword123",
                "new_password": "NewPassword456"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

        # Verify old password doesn't work
        old_login = client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "OldPassword123"
        })
        assert old_login.status_code == 401

        # Verify new password works
        new_login = client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "NewPassword456"
        })
        assert new_login.status_code == 200

    def test_change_password_wrong_old(self, client, db_session):
        """Test password change with wrong old password."""
        from app.services.user_service import UserService
        user_service = UserService(db_session)
        user = user_service.create_user(
            email="user@example.com",
            username="testuser",
            password="CorrectPassword123"
        )

        login_response = client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "CorrectPassword123"
        })
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "WrongPassword123",
                "new_password": "NewPassword456"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 401

    def test_change_password_short_new(self, client, db_session):
        """Test password change with short new password."""
        from app.services.user_service import UserService
        user_service = UserService(db_session)
        user = user_service.create_user(
            email="user@example.com",
            username="testuser",
            password="Password123"
        )

        login_response = client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "Password123"
        })
        token = login_response.json()["access_token"]

        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "Password123",
                "new_password": "short"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400


class TestGetCurrentUser:
    """Test getting current user info."""

    def test_get_current_user_success(self, client, db_session):
        """Test successful retrieval of current user."""
        from app.services.user_service import UserService
        user_service = UserService(db_session)
        user_service.create_user(
            email="user@example.com",
            username="testuser",
            password="Password123"
        )

        login_response = client.post("/api/v1/auth/login", json={
            "email": "user@example.com",
            "password": "Password123"
        })
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "user@example.com"
        assert data["username"] == "testuser"
        assert data["is_active"] is True

    def test_get_current_user_no_token(self, client):
        """Test getting current user without token."""
        response = client.get("/api/v1/auth/me")

        assert response.status_code in [401, 403]  # Unauthorized
