"""Unit tests for automatic user provisioning."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from app.core.security import get_current_user
from app.repositories.user_repo import UserRepository


class TestAutoProvisioning:
    """Test automatic user provisioning from .NET API."""

    @pytest.mark.asyncio
    async def test_get_current_user_upserts_user_from_net_api(self):
        """Test that get_current_user UPSERTs user from .NET API."""
        # Mock JWT payload
        mock_payload = {
            "sub": "test-user-123",
            "email": "test@example.com",
            "name": "Test User"
        }

        # Mock .NET API response
        mock_api_data = {
            "fullName": "Test User",
            "firstName": "Test",
            "lastName": "User",
            "gender": "Male",
            "birthDate": "2004-02-06T00:00:00",
            "city": "cairo",
            "governorate": None,
            "university": None,
            "fieldOfStudy": None,
            "jobTitle": None,
            "aboutMe": None,
            "status": "Pending",
            "isProfileComplete": True
        }

        with patch("app.core.security.jwt.decode", return_value=mock_payload):
            with patch.object(UserRepository, "ensure_user_exists", new_callable=AsyncMock) as mock_ensure:
                mock_ensure.return_value = MagicMock(id="local-id-123")
                
                # Mock credentials
                mock_credentials = MagicMock()
                mock_credentials.credentials = "fake-jwt-token"
                
                # Call get_current_user
                result = await get_current_user(mock_credentials)
                
                # Verify user was provisioned
                mock_ensure.assert_called_once_with("test-user-123")
                
                # Verify result
                assert result.user_id == "test-user-123"
                assert result.email == "test@example.com"
                assert result.name == "Test User"

    @pytest.mark.asyncio
    async def test_upsert_creates_new_user(self):
        """Test that upsert creates new user when not exists."""
        # Mock .NET API response
        mock_api_data = {
            "fullName": "New User",
            "firstName": "New",
            "lastName": "User",
            "gender": "Male",
            "birthDate": "2004-02-06T00:00:00",
            "city": "cairo",
            "governorate": None,
            "university": None,
            "fieldOfStudy": None,
            "jobTitle": None,
            "aboutMe": None,
            "status": "Pending",
            "isProfileComplete": True
        }

        user_repo = UserRepository()
        
        with patch.object(user_repo, "get_by_external_id", return_value=None):
            with patch.object(user_repo.session, "add") as mock_add:
                with patch.object(user_repo.session, "commit"):
                    with patch.object(user_repo.session, "refresh"):
                        result = user_repo.upsert_from_api_data("new-user-123", mock_api_data)
                        
                        # Verify add was called (new user creation)
                        mock_add.assert_called_once()
        
        user_repo.close()

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_user(self):
        """Test that upsert updates existing user."""
        # Mock existing user
        existing_user = MagicMock()
        existing_user.full_name = "Old Name"
        
        # Mock .NET API response
        mock_api_data = {
            "fullName": "Updated Name",
            "firstName": "Updated",
            "lastName": "Name",
            "gender": "Male",
            "birthDate": "2004-02-06T00:00:00",
            "city": "giza",
            "governorate": None,
            "university": None,
            "fieldOfStudy": None,
            "jobTitle": "Engineer",
            "aboutMe": "About me",
            "status": "Active",
            "isProfileComplete": True
        }

        user_repo = UserRepository()
        
        with patch.object(user_repo, "get_by_external_id", return_value=existing_user):
            with patch.object(user_repo.session, "commit"):
                with patch.object(user_repo.session, "refresh"):
                    result = user_repo.upsert_from_api_data("existing-user-123", mock_api_data)
                    
                    # Verify existing user was updated
                    assert existing_user.full_name == "Updated Name"
                    assert existing_user.city == "giza"
                    assert existing_user.job_title == "Engineer"
        
        user_repo.close()
