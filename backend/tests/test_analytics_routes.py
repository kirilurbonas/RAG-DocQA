"""Tests for analytics routes."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.models import Base
from app.db.database import get_db
from app.services.user_service import UserService
from app.services.analytics_service import AnalyticsService


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


@pytest.fixture
def admin_token(client, db_session):
    """Create an admin user and return auth token."""
    user_service = UserService(db_session)
    user_service.create_user(
        email="admin@example.com",
        username="admin",
        password="Password123",
        is_admin=True
    )

    response = client.post("/api/v1/auth/login", json={
        "email": "admin@example.com",
        "password": "Password123"
    })

    return response.json()["access_token"]


class TestUserStats:
    """Test user statistics endpoint."""

    def test_get_user_stats(self, client, auth_token, db_session):
        """Test getting user statistics."""
        # Add some events
        user_service = UserService(db_session)
        user = user_service.authenticate_user("user@example.com", "Password123")

        analytics = AnalyticsService(db_session)
        analytics.track_event(user['id'], "ask", token_count=100, latency_ms=2000)
        analytics.track_event(user['id'], "ask", token_count=150, latency_ms=2500)
        analytics.track_event(user['id'], "upload", token_count=0, latency_ms=1000)

        response = client.get(
            "/api/v1/analytics/user/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 3
        assert data["total_tokens"] == 250
        assert "ask" in data["events_by_type"]
        assert data["events_by_type"]["ask"] == 2

    def test_get_user_stats_no_auth(self, client):
        """Test getting stats without authentication."""
        response = client.get("/api/v1/analytics/user/stats")

        assert response.status_code in [401, 403]

    def test_get_user_stats_with_days_filter(self, client, auth_token, db_session):
        """Test getting stats with time window filter."""
        user_service = UserService(db_session)
        user = user_service.authenticate_user("user@example.com", "Password123")

        analytics = AnalyticsService(db_session)
        analytics.track_event(user['id'], "ask", token_count=100)

        response = client.get(
            "/api/v1/analytics/user/stats?days=30",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 30


class TestAggregateStats:
    """Test aggregate statistics endpoint."""

    def test_get_aggregate_stats_admin(self, client, admin_token, db_session):
        """Test getting aggregate stats as admin."""
        # Add events from multiple users
        user_service = UserService(db_session)
        user1 = user_service.authenticate_user("user@example.com", "Password123")
        user2 = user_service.create_user(
            email="user2@example.com",
            username="user2",
            password="Password123"
        )

        analytics = AnalyticsService(db_session)
        analytics.track_event(user1['id'], "ask", token_count=100)
        analytics.track_event(user1['id'], "ask", token_count=100)
        analytics.track_event(user2['id'], "upload", token_count=0)

        response = client.get(
            "/api/v1/analytics/aggregate/stats",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 3
        assert data["unique_users"] == 2
        assert data["total_tokens"] == 200

    def test_get_aggregate_stats_non_admin(self, client, auth_token):
        """Test that non-admin users cannot access aggregate stats."""
        response = client.get(
            "/api/v1/analytics/aggregate/stats",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        # Should return empty or error
        assert response.status_code == 200
        data = response.json()
        assert "error" in data or "Admin access required" in str(data)


class TestTopUsers:
    """Test top users ranking endpoint."""

    def test_get_top_users_by_events(self, client, admin_token, db_session):
        """Test getting top users by event count."""
        user_service = UserService(db_session)
        user1 = user_service.authenticate_user("user@example.com", "Password123")
        user2 = user_service.create_user(
            email="user2@example.com",
            username="user2",
            password="Password123"
        )

        analytics = AnalyticsService(db_session)
        for _ in range(5):
            analytics.track_event(user1['id'], "ask")
        for _ in range(3):
            analytics.track_event(user2['id'], "ask")

        response = client.get(
            "/api/v1/analytics/top-users?metric=events",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["event_count"] == 5

    def test_get_top_users_by_tokens(self, client, admin_token, db_session):
        """Test getting top users by token count."""
        user_service = UserService(db_session)
        user1 = user_service.authenticate_user("user@example.com", "Password123")
        user2 = user_service.create_user(
            email="user2@example.com",
            username="user2",
            password="Password123"
        )

        analytics = AnalyticsService(db_session)
        analytics.track_event(user1['id'], "ask", token_count=1000)
        analytics.track_event(user2['id'], "ask", token_count=500)

        response = client.get(
            "/api/v1/analytics/top-users?metric=tokens",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert data[0]["total_tokens"] == 1000

    def test_get_top_users_non_admin(self, client, auth_token):
        """Test that non-admin users cannot access top users."""
        response = client.get(
            "/api/v1/analytics/top-users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # Non-admin gets empty list
