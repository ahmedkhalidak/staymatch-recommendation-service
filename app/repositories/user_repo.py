"""User repository for managing user profiles."""
import logging
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.database.session import get_session
from app.database.models.user import UserProfile
from app.services.property_api_client import PropertyAPIClient

logger = logging.getLogger("staymatch.user_repo")


class UserRepository:
    """Repository for user profile operations."""

    def __init__(self, token: Optional[str] = None):
        self.session = get_session()
        self.api_client = PropertyAPIClient(token=token)

    def get_by_external_id(self, external_user_id: str) -> Optional[UserProfile]:
        """Get user profile by external_user_id."""
        return self.session.query(UserProfile).filter(
            UserProfile.external_user_id == external_user_id
        ).first()

    def upsert_from_api_data(self, external_user_id: str, api_data: dict) -> UserProfile:
        """
        Create or update user profile from .NET API data.
        
        Implements UPSERT strategy:
        - If user doesn't exist: create new record
        - If user exists: update with latest data from .NET API
        
        Args:
            external_user_id: User ID from JWT
            api_data: User profile data from .NET API
            
        Returns:
            UserProfile instance
        """
        # Parse birth date to extract birth year
        birth_date = api_data.get("birthDate")
        birth_year = None
        if birth_date:
            try:
                if isinstance(birth_date, str):
                    birth_date = datetime.fromisoformat(birth_date.replace('Z', '+00:00'))
                birth_year = birth_date.year
            except (ValueError, AttributeError):
                logger.warning(f"Failed to parse birth date: {birth_date}")

        # Check if user already exists
        existing_user = self.get_by_external_id(external_user_id)
        
        if existing_user:
            # Update existing user
            existing_user.full_name = api_data.get("fullName")
            existing_user.first_name = api_data.get("firstName")
            existing_user.last_name = api_data.get("lastName")
            existing_user.gender = api_data.get("gender")
            existing_user.birth_date = birth_date
            existing_user.birth_year = birth_year
            existing_user.city = api_data.get("city")
            existing_user.governorate = api_data.get("governorate")
            existing_user.university = api_data.get("university")
            existing_user.field_of_study = api_data.get("fieldOfStudy")
            existing_user.job_title = api_data.get("jobTitle")
            existing_user.about_me = api_data.get("aboutMe")
            existing_user.status = api_data.get("status")
            existing_user.is_profile_complete = api_data.get("isProfileComplete", False)
            
            self.session.commit()
            self.session.refresh(existing_user)
            logger.info(f"Updated user profile for external_user_id: {external_user_id}")
            return existing_user
        else:
            # Create new user
            user_profile = UserProfile(
                external_user_id=external_user_id,
                full_name=api_data.get("fullName"),
                first_name=api_data.get("firstName"),
                last_name=api_data.get("lastName"),
                gender=api_data.get("gender"),
                birth_date=birth_date,
                birth_year=birth_year,
                city=api_data.get("city"),
                governorate=api_data.get("governorate"),
                university=api_data.get("university"),
                field_of_study=api_data.get("fieldOfStudy"),
                job_title=api_data.get("jobTitle"),
                about_me=api_data.get("aboutMe"),
                status=api_data.get("status"),
                is_profile_complete=api_data.get("isProfileComplete", False),
            )
            self.session.add(user_profile)
            self.session.commit()
            self.session.refresh(user_profile)
            logger.info(f"Created user profile for external_user_id: {external_user_id}")
            return user_profile

    async def ensure_user_exists(self, external_user_id: str) -> UserProfile:
        """
        Ensure user exists in local database with latest data from .NET API.
        
        Implements UPSERT strategy:
        - If user doesn't exist: fetch from .NET API and create
        - If user exists: fetch from .NET API and update
        
        Args:
            external_user_id: User ID from JWT
            
        Returns:
            UserProfile instance
        """
        # Fetch from .NET API (always fetch to get latest data)
        logger.info(f"Fetching profile for {external_user_id} from .NET API")
        api_data = await self.api_client.get_current_user_profile()
        
        if not api_data:
            logger.error(f"Failed to fetch user profile from .NET API: {external_user_id}")
            raise ValueError(f"User not found in .NET API: {external_user_id}")

        logger.info(f"Successfully fetched profile for {external_user_id}")
        # Upsert user profile (create or update)
        return self.upsert_from_api_data(external_user_id, api_data)

    def close(self):
        """Close the database session."""
        self.session.close()
