"""Team management endpoints."""

from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List

from app.db.database import get_db
from app.services.user_service import UserService
from app.security.auth import get_current_user

router = APIRouter(prefix="/teams", tags=["teams"])


class TeamCreate(BaseModel):
    """Create team request."""
    name: str


class TeamMemberResponse(BaseModel):
    """Team member info."""
    user_id: str
    role: str


class TeamResponse(BaseModel):
    """Team info."""
    id: str
    name: str
    owner_id: str
    members: List[TeamMemberResponse] = []


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    request: TeamCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Create a new team."""
    user_service = UserService(db)
    team = user_service.create_team(current_user['id'], request.name)

    return TeamResponse(
        id=team['id'],
        name=team['name'],
        owner_id=team['owner_id']
    )


@router.get("", response_model=List[TeamResponse])
async def get_user_teams(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all teams for current user."""
    user_service = UserService(db)
    teams = user_service.get_user_teams(current_user['id'])

    return [
        TeamResponse(
            id=team['id'],
            name=team['name'],
            owner_id=team.get('owner_id', ''),
            members=[]
        )
        for team in teams
    ]


@router.post("/{team_id}/members")
async def add_team_member(
    team_id: str,
    user_id: str,
    role: str = "member",
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Add a member to a team."""
    user_service = UserService(db)
    success = user_service.add_team_member(team_id, user_id, role)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to add team member"
        )

    return {"message": "Member added successfully"}
