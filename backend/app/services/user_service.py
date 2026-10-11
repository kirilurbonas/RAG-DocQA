"""User account management service."""

import logging
from typing import Optional, Dict, List
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.orm import Session

from app.db.models import User, Team, TeamMember, Share
from app.services.password_service import get_password_service

logger = logging.getLogger(__name__)


class UserService:
    """Manage user accounts and authentication."""

    def __init__(self, db: Session):
        """Initialize user service."""
        self.db = db
        self.password_service = get_password_service()

    def create_user(
        self,
        email: str,
        username: str,
        password: str,
        is_admin: bool = False
    ) -> Optional[Dict]:
        """
        Create a new user account.

        Args:
            email: User email
            username: Username
            password: Plain text password (will be hashed)
            is_admin: Whether user is admin

        Returns:
            User dict or None if creation failed
        """
        # Validate inputs
        if not email or '@' not in email:
            raise ValueError("Invalid email address")
        if not username or len(username) < 3:
            raise ValueError("Username must be at least 3 characters")

        # Check if user already exists
        existing = self.db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        if existing:
            raise ValueError("Email or username already in use")

        # Hash password
        password_hash = self.password_service.hash_password(password)

        # Create user
        user = User(
            id=str(uuid4()),
            email=email,
            username=username,
            password_hash=password_hash,
            is_admin=is_admin
        )

        try:
            self.db.add(user)
            self.db.commit()
            logger.info(f"Created user {username}")
            return self._to_dict(user)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create user: {e}")
            raise

    def authenticate_user(self, email: str, password: str) -> Optional[Dict]:
        """
        Authenticate a user by email and password.

        Args:
            email: User email
            password: Plain text password

        Returns:
            User dict if authenticated, None otherwise
        """
        user = self.db.query(User).filter(User.email == email).first()

        if not user or not self.password_service.verify_password(password, user.password_hash):
            return None

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        self.db.commit()

        return self._to_dict(user)

    def get_user(self, user_id: str) -> Optional[Dict]:
        """
        Get user by ID.

        Args:
            user_id: User ID

        Returns:
            User dict or None
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        return self._to_dict(user) if user else None

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email."""
        user = self.db.query(User).filter(User.email == email).first()
        return self._to_dict(user) if user else None

    def update_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """
        Update user password.

        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password

        Returns:
            True if successful
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        if not self.password_service.verify_password(old_password, user.password_hash):
            return False

        user.password_hash = self.password_service.hash_password(new_password)
        self.db.commit()
        logger.info(f"Updated password for user {user_id}")
        return True

    def deactivate_user(self, user_id: str) -> bool:
        """
        Deactivate a user account.

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        user.is_active = False
        self.db.commit()
        logger.info(f"Deactivated user {user_id}")
        return True

    def create_team(self, owner_id: str, name: str) -> Optional[Dict]:
        """
        Create a team.

        Args:
            owner_id: Team owner user ID
            name: Team name

        Returns:
            Team dict or None
        """
        team = Team(
            id=str(uuid4()),
            owner_id=owner_id,
            name=name
        )

        try:
            self.db.add(team)

            # Add owner as team member
            member = TeamMember(
                team_id=team.id,
                user_id=owner_id,
                role='owner'
            )
            self.db.add(member)
            self.db.commit()
            logger.info(f"Created team {team.id}")
            return self._team_to_dict(team)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create team: {e}")
            raise

    def add_team_member(self, team_id: str, user_id: str, role: str = 'member') -> bool:
        """
        Add a member to a team.

        Args:
            team_id: Team ID
            user_id: User ID to add
            role: Role (owner, admin, member)

        Returns:
            True if successful
        """
        # Check user exists
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        # Check membership doesn't exist
        existing = self.db.query(TeamMember).filter(
            (TeamMember.team_id == team_id) & (TeamMember.user_id == user_id)
        ).first()
        if existing:
            return False

        member = TeamMember(team_id=team_id, user_id=user_id, role=role)
        self.db.add(member)
        self.db.commit()
        logger.info(f"Added user {user_id} to team {team_id}")
        return True

    def get_user_teams(self, user_id: str) -> List[Dict]:
        """
        Get all teams for a user.

        Args:
            user_id: User ID

        Returns:
            List of team dicts
        """
        members = self.db.query(TeamMember).filter(
            TeamMember.user_id == user_id
        ).all()

        teams = []
        for member in members:
            team_dict = self._team_to_dict(member.team)
            team_dict['role'] = member.role
            teams.append(team_dict)

        return teams

    def share_resource(
        self,
        resource_type: str,
        resource_id: str,
        owner_id: str,
        shared_with_user_id: Optional[str] = None,
        shared_with_team_id: Optional[str] = None,
        permission: str = 'read'
    ) -> Optional[Dict]:
        """
        Share a resource with another user or team.

        Args:
            resource_type: Type of resource (document, conversation)
            resource_id: Resource ID
            owner_id: Resource owner ID
            shared_with_user_id: User to share with (or None for team)
            shared_with_team_id: Team to share with (or None for user)
            permission: Permission level (read, write)

        Returns:
            Share dict or None
        """
        share = Share(
            id=str(uuid4()),
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
            shared_with_user_id=shared_with_user_id,
            shared_with_team_id=shared_with_team_id,
            permission=permission
        )

        try:
            self.db.add(share)
            self.db.commit()
            logger.info(f"Shared {resource_type} {resource_id}")
            return self._share_to_dict(share)
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to share resource: {e}")
            raise

    def revoke_share(self, share_id: str) -> bool:
        """
        Revoke a share.

        Args:
            share_id: Share ID

        Returns:
            True if successful
        """
        share = self.db.query(Share).filter(Share.id == share_id).first()
        if not share:
            return False

        self.db.delete(share)
        self.db.commit()
        logger.info(f"Revoked share {share_id}")
        return True

    @staticmethod
    def _to_dict(user: User) -> Dict:
        """Convert user ORM to dict."""
        if not user:
            return None
        return {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'is_active': user.is_active,
            'is_admin': user.is_admin,
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'last_login': user.last_login.isoformat() if user.last_login else None,
        }

    @staticmethod
    def _team_to_dict(team: Team) -> Dict:
        """Convert team ORM to dict."""
        if not team:
            return None
        return {
            'id': team.id,
            'name': team.name,
            'owner_id': team.owner_id,
            'created_at': team.created_at.isoformat() if team.created_at else None,
            'member_count': len(team.members)
        }

    @staticmethod
    def _share_to_dict(share: Share) -> Dict:
        """Convert share ORM to dict."""
        if not share:
            return None
        return {
            'id': share.id,
            'resource_type': share.resource_type,
            'resource_id': share.resource_id,
            'owner_id': share.owner_id,
            'shared_with_user_id': share.shared_with_user_id,
            'shared_with_team_id': share.shared_with_team_id,
            'permission': share.permission,
            'created_at': share.created_at.isoformat() if share.created_at else None,
        }
