"""Comprehensive tests for user accounts and analytics (Phase 6)."""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from uuid import uuid4

from app.db.models import Base, User, Team, TeamMember, Share, UsageEvent
from app.services.password_service import PasswordService, get_password_service
from app.services.user_service import UserService
from app.services.analytics_service import AnalyticsService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


class TestPasswordService:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test password hashing."""
        service = PasswordService()
        password = "MySecurePassword123"

        hashed = service.hash_password(password)

        assert hashed != password
        assert len(hashed) > 20
        assert "$argon2" in hashed

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        service = PasswordService()
        password = "MySecurePassword123"
        hashed = service.hash_password(password)

        assert service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        service = PasswordService()
        password = "MySecurePassword123"
        hashed = service.hash_password(password)

        assert service.verify_password("WrongPassword", hashed) is False

    def test_hash_password_too_short(self):
        """Test that short passwords are rejected."""
        service = PasswordService()

        with pytest.raises(ValueError, match="at least 8 characters"):
            service.hash_password("short")

    def test_hash_password_empty(self):
        """Test that empty passwords are rejected."""
        service = PasswordService()

        with pytest.raises(ValueError):
            service.hash_password("")

    def test_verify_password_empty(self):
        """Test verifying with empty password."""
        service = PasswordService()

        assert service.verify_password("", "somehash") is False
        assert service.verify_password("password", "") is False

    def test_get_password_service(self):
        """Test getting password service singleton."""
        service1 = get_password_service()
        service2 = get_password_service()

        assert service1 is service2


class TestUserService:
    """Test user account management."""

    def test_create_user(self, db_session):
        """Test creating a user."""
        service = UserService(db_session)

        user = service.create_user(
            email="test@example.com",
            username="testuser",
            password="SecurePass123"
        )

        assert user is not None
        assert user['email'] == "test@example.com"
        assert user['username'] == "testuser"
        assert user['is_active'] is True
        assert user['is_admin'] is False

    def test_create_admin_user(self, db_session):
        """Test creating an admin user."""
        service = UserService(db_session)

        user = service.create_user(
            email="admin@example.com",
            username="admin",
            password="AdminPass123",
            is_admin=True
        )

        assert user['is_admin'] is True

    def test_create_user_duplicate_email(self, db_session):
        """Test that duplicate emails are rejected."""
        service = UserService(db_session)
        service.create_user(
            email="test@example.com",
            username="user1",
            password="SecurePass123"
        )

        with pytest.raises(ValueError, match="already in use"):
            service.create_user(
                email="test@example.com",
                username="user2",
                password="SecurePass123"
            )

    def test_create_user_duplicate_username(self, db_session):
        """Test that duplicate usernames are rejected."""
        service = UserService(db_session)
        service.create_user(
            email="test1@example.com",
            username="testuser",
            password="SecurePass123"
        )

        with pytest.raises(ValueError, match="already in use"):
            service.create_user(
                email="test2@example.com",
                username="testuser",
                password="SecurePass123"
            )

    def test_authenticate_user_correct(self, db_session):
        """Test authenticating with correct credentials."""
        service = UserService(db_session)
        service.create_user(
            email="test@example.com",
            username="testuser",
            password="SecurePass123"
        )

        user = service.authenticate_user("test@example.com", "SecurePass123")

        assert user is not None
        assert user['email'] == "test@example.com"

    def test_authenticate_user_wrong_password(self, db_session):
        """Test authentication with wrong password."""
        service = UserService(db_session)
        service.create_user(
            email="test@example.com",
            username="testuser",
            password="SecurePass123"
        )

        user = service.authenticate_user("test@example.com", "WrongPassword")

        assert user is None

    def test_authenticate_user_nonexistent(self, db_session):
        """Test authentication with nonexistent user."""
        service = UserService(db_session)

        user = service.authenticate_user("nonexistent@example.com", "password")

        assert user is None

    def test_update_last_login(self, db_session):
        """Test that last_login is updated on authentication."""
        service = UserService(db_session)
        service.create_user(
            email="test@example.com",
            username="testuser",
            password="SecurePass123"
        )

        user1 = service.authenticate_user("test@example.com", "SecurePass123")
        assert user1['last_login'] is not None

    def test_update_password(self, db_session):
        """Test updating user password."""
        service = UserService(db_session)
        user_dict = service.create_user(
            email="test@example.com",
            username="testuser",
            password="OldPassword123"
        )

        success = service.update_password(
            user_dict['id'],
            "OldPassword123",
            "NewPassword456"
        )

        assert success is True

        # Verify old password doesn't work
        result = service.authenticate_user("test@example.com", "OldPassword123")
        assert result is None

        # Verify new password works
        result = service.authenticate_user("test@example.com", "NewPassword456")
        assert result is not None

    def test_deactivate_user(self, db_session):
        """Test deactivating a user."""
        service = UserService(db_session)
        user_dict = service.create_user(
            email="test@example.com",
            username="testuser",
            password="SecurePass123"
        )

        success = service.deactivate_user(user_dict['id'])

        assert success is True

        user = db_session.query(User).filter(User.id == user_dict['id']).first()
        assert user.is_active is False

    def test_create_team(self, db_session):
        """Test creating a team."""
        service = UserService(db_session)
        user_dict = service.create_user(
            email="test@example.com",
            username="testuser",
            password="SecurePass123"
        )

        team = service.create_team(user_dict['id'], "Test Team")

        assert team is not None
        assert team['name'] == "Test Team"
        assert team['owner_id'] == user_dict['id']

    def test_add_team_member(self, db_session):
        """Test adding a member to a team."""
        service = UserService(db_session)
        user1 = service.create_user(
            email="user1@example.com",
            username="user1",
            password="SecurePass123"
        )
        user2 = service.create_user(
            email="user2@example.com",
            username="user2",
            password="SecurePass123"
        )
        team = service.create_team(user1['id'], "Test Team")

        success = service.add_team_member(team['id'], user2['id'], role='member')

        assert success is True

    def test_get_user_teams(self, db_session):
        """Test getting user's teams."""
        service = UserService(db_session)
        user = service.create_user(
            email="test@example.com",
            username="testuser",
            password="SecurePass123"
        )
        team = service.create_team(user['id'], "Test Team")

        teams = service.get_user_teams(user['id'])

        assert len(teams) == 1
        assert teams[0]['id'] == team['id']
        assert teams[0]['role'] == 'owner'

    def test_share_resource(self, db_session):
        """Test sharing a resource."""
        service = UserService(db_session)
        user1 = service.create_user(
            email="user1@example.com",
            username="user1",
            password="SecurePass123"
        )
        user2 = service.create_user(
            email="user2@example.com",
            username="user2",
            password="SecurePass123"
        )

        share = service.share_resource(
            resource_type="document",
            resource_id="doc-123",
            owner_id=user1['id'],
            shared_with_user_id=user2['id'],
            permission="read"
        )

        assert share is not None
        assert share['resource_type'] == "document"
        assert share['shared_with_user_id'] == user2['id']

    def test_revoke_share(self, db_session):
        """Test revoking a share."""
        service = UserService(db_session)
        user1 = service.create_user(
            email="user1@example.com",
            username="user1",
            password="SecurePass123"
        )
        user2 = service.create_user(
            email="user2@example.com",
            username="user2",
            password="SecurePass123"
        )
        share = service.share_resource(
            resource_type="document",
            resource_id="doc-123",
            owner_id=user1['id'],
            shared_with_user_id=user2['id']
        )

        success = service.revoke_share(share['id'])

        assert success is True


class TestAnalyticsService:
    """Test analytics and usage tracking."""

    def test_track_event(self, db_session):
        """Test tracking a usage event."""
        service = AnalyticsService(db_session)
        user_id = str(uuid4())

        event = service.track_event(
            user_id=user_id,
            event_type="ask",
            token_count=100,
            latency_ms=250.5,
            success=True
        )

        assert event is not None
        assert event['user_id'] == user_id
        assert event['event_type'] == "ask"
        assert event['token_count'] == 100
        assert event['latency_ms'] == 250.5
        assert event['success'] is True

    def test_track_failed_event(self, db_session):
        """Test tracking a failed event."""
        service = AnalyticsService(db_session)
        user_id = str(uuid4())

        event = service.track_event(
            user_id=user_id,
            event_type="upload",
            success=False
        )

        assert event['success'] is False

    def test_get_user_stats(self, db_session):
        """Test getting user statistics."""
        service = AnalyticsService(db_session)
        user_id = str(uuid4())

        # Track some events
        service.track_event(user_id, "ask", token_count=100, latency_ms=250)
        service.track_event(user_id, "ask", token_count=150, latency_ms=300)
        service.track_event(user_id, "upload", token_count=0, latency_ms=100)

        stats = service.get_user_stats(user_id)

        assert stats['user_id'] == user_id
        assert stats['total_events'] == 3
        assert stats['total_tokens'] == 250
        assert stats['events_by_type']['ask'] == 2
        assert stats['events_by_type']['upload'] == 1

    def test_get_user_stats_no_events(self, db_session):
        """Test getting stats for user with no events."""
        service = AnalyticsService(db_session)
        user_id = str(uuid4())

        stats = service.get_user_stats(user_id)

        assert stats['total_events'] == 0
        assert stats['success_rate'] == 0

    def test_success_rate_calculation(self, db_session):
        """Test success rate calculation."""
        service = AnalyticsService(db_session)
        user_id = str(uuid4())

        service.track_event(user_id, "ask", success=True)
        service.track_event(user_id, "ask", success=True)
        service.track_event(user_id, "ask", success=False)

        stats = service.get_user_stats(user_id)

        assert abs(stats['success_rate'] - 2/3) < 0.01

    def test_get_aggregate_stats(self, db_session):
        """Test getting aggregate statistics."""
        service = AnalyticsService(db_session)

        user1 = str(uuid4())
        user2 = str(uuid4())

        service.track_event(user1, "ask", token_count=100)
        service.track_event(user1, "upload", token_count=0)
        service.track_event(user2, "ask", token_count=200)

        stats = service.get_aggregate_stats()

        assert stats['total_events'] == 3
        assert stats['unique_users'] == 2
        assert stats['total_tokens'] == 300
        assert stats['events_by_type']['ask'] == 2

    def test_get_top_users_by_events(self, db_session):
        """Test getting top users by event count."""
        service = AnalyticsService(db_session)

        user1 = str(uuid4())
        user2 = str(uuid4())

        for _ in range(5):
            service.track_event(user1, "ask")
        for _ in range(3):
            service.track_event(user2, "ask")

        top_users = service.get_top_users(metric='events', limit=10)

        assert len(top_users) == 2
        assert top_users[0]['user_id'] == user1
        assert top_users[0]['event_count'] == 5

    def test_average_latency_calculation(self, db_session):
        """Test average latency calculation."""
        service = AnalyticsService(db_session)
        user_id = str(uuid4())

        service.track_event(user_id, "ask", latency_ms=100)
        service.track_event(user_id, "ask", latency_ms=200)
        service.track_event(user_id, "ask", latency_ms=300)

        stats = service.get_user_stats(user_id)

        assert stats['avg_latency_ms'] == 200

    def test_stats_time_window(self, db_session):
        """Test that stats respect time window."""
        service = AnalyticsService(db_session)
        user_id = str(uuid4())

        # Create event now
        service.track_event(user_id, "ask")

        # Create old event manually
        old_event = UsageEvent(
            id=str(uuid4()),
            user_id=user_id,
            event_type="ask",
            created_at=datetime.now(timezone.utc) - timedelta(days=40)
        )
        db_session.add(old_event)
        db_session.commit()

        # Stats for 30 days should only include recent event
        stats = service.get_user_stats(user_id, days=30)
        assert stats['total_events'] == 1

        # Stats for 50 days should include both
        stats = service.get_user_stats(user_id, days=50)
        assert stats['total_events'] == 2


class TestUserIntegration:
    """Integration tests for user management."""

    def test_user_team_workflow(self, db_session):
        """Test complete user and team workflow."""
        user_service = UserService(db_session)

        # Create users
        user1 = user_service.create_user(
            email="owner@example.com",
            username="owner",
            password="SecurePass123"
        )
        user2 = user_service.create_user(
            email="member@example.com",
            username="member",
            password="SecurePass123"
        )

        # Create team
        team = user_service.create_team(user1['id'], "Development Team")

        # Add member
        user_service.add_team_member(team['id'], user2['id'], role='member')

        # Get teams for both users
        user1_teams = user_service.get_user_teams(user1['id'])
        user2_teams = user_service.get_user_teams(user2['id'])

        assert len(user1_teams) == 1
        assert user1_teams[0]['role'] == 'owner'
        assert len(user2_teams) == 1
        assert user2_teams[0]['role'] == 'member'

    def test_usage_tracking_workflow(self, db_session):
        """Test complete usage tracking workflow."""
        user_service = UserService(db_session)
        analytics_service = AnalyticsService(db_session)

        # Create user
        user = user_service.create_user(
            email="user@example.com",
            username="user",
            password="SecurePass123"
        )

        # Track various events
        analytics_service.track_event(user['id'], "ask", token_count=100, latency_ms=250)
        analytics_service.track_event(user['id'], "upload", token_count=0, latency_ms=150)
        analytics_service.track_event(user['id'], "ask", token_count=50, latency_ms=200, success=False)

        # Get user stats
        stats = analytics_service.get_user_stats(user['id'])

        assert stats['total_events'] == 3
        assert stats['total_tokens'] == 150
        assert abs(stats['success_rate'] - 2/3) < 0.01
