"""API client for .NET Property API endpoints."""
import logging
from typing import Optional, List, Dict, Any
import httpx
import asyncio

from app.config import settings

logger = logging.getLogger("staymatch.property_api")


class PropertyAPIClient:
    """Client for fetching property and room data from .NET API."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: float = 30.0, token: Optional[str] = None):
        self.base_url = (base_url or settings.PROPERTY_API_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.token = token or settings.PROPERTY_API_TOKEN
        self._client: Optional[httpx.AsyncClient] = None
        print(f"[PropertyAPIClient] TOKEN = {self.token[:30] if self.token else None}...")
    
    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
                print(f"[PropertyAPIClient] AUTH HEADER = {headers['Authorization'][:50]}...")
            print(f"[PropertyAPIClient] Headers = {headers}")
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self._client
    
    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request to .NET API."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                # Handle 404 as empty result
                return {"isSuccess": False, "message": "Not found", "data": None}
            logger.error(f"API request failed: {url} - {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"API request failed: {url} - {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            raise
    
    async def get_all_properties_with_rooms(self, only_available: bool = True, page_size: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch all properties with their rooms.
        
        GET /api/Property/GetAllWithRooms
        
        Returns list of properties with nested rooms.
        """
        try:
            params = {
                "onlyAvailable": only_available,
                "pageSize": page_size,
                "page": 1
            }
            result = await self._get("/api/Property/GetAllWithRooms", params=params)
            return result.get("data", {}).get("items", [])
        except Exception as e:
            logger.error(f"Failed to fetch properties with rooms: {e}")
            return []
    
    async def get_room_details(self, property_id: int, room_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed room information.
        
        GET /api/Property/{propertyId}/rooms/{roomId}
        
        Returns room details including allowedTenants, capacity, etc.
        """
        try:
            result = await self._get(f"/api/Property/{property_id}/rooms/{room_id}")
            if result.get("isSuccess") and result.get("data"):
                return result["data"]
            return None
        except Exception as e:
            logger.error(f"Failed to fetch room details for property {property_id}, room {room_id}: {e}")
            return None
    
    async def get_room_occupants(self, room_id: int) -> List[str]:
        """
        Fetch current occupants for a room.
        
        GET /api/Property/Room/occupants?id={roomId}
        
        Returns list of user GUIDs. Empty list if no occupants.
        """
        try:
            result = await self._get("/api/Property/Room/occupants", params={"id": room_id})
            if result.get("isSuccess") and result.get("data"):
                return result["data"]
            return []
        except Exception as e:
            logger.error(f"Failed to fetch occupants for room {room_id}: {e}")
            return []
    
    async def get_property_occupants(self, property_id: int) -> List[Dict[str, Any]]:
        """
        Fetch all occupants for a property with their room assignments.
        
        GET /api/Property/Property/occupants?id={propertyId}
        
        Returns list of occupants with userId and roomId.
        """
        try:
            result = await self._get("/api/Property/Property/occupants", params={"id": property_id})
            if result.get("isSuccess") and result.get("data"):
                return result["data"].get("occupants", [])
            return []
        except Exception as e:
            logger.error(f"Failed to fetch occupants for property {property_id}: {e}")
            return []
    
    async def get_multiple_property_occupants(self, property_ids: List[int], max_concurrent: int = 20) -> Dict[int, List[Dict[str, Any]]]:
        """
        Fetch occupants for multiple properties in parallel with rate limiting.
        
        Args:
            property_ids: List of property IDs to fetch occupants for
            max_concurrent: Maximum number of concurrent requests (default: 20)
        
        Returns:
            Dictionary mapping property_id to list of occupants
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def fetch_with_limit(pid: int):
            async with semaphore:
                return await self.get_property_occupants(pid)
        
        tasks = [fetch_with_limit(pid) for pid in property_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        occupants_map = {}
        for pid, result in zip(property_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching occupants for property {pid}: {result}")
                occupants_map[pid] = []
            else:
                occupants_map[pid] = result
        
        return occupants_map
    
    async def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch user profile by ID.
        
        GET /api/ViewUserProfile/{userId}
        """
        try:
            result = await self._get(f"/api/ViewUserProfile/{user_id}")
            if result.get("success") and result.get("data"):
                return result["data"]
            return None
        except Exception as e:
            logger.error(f"Failed to fetch user profile for {user_id}: {e}")
            return None
    
    async def get_current_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        Fetch current user profile.
        
        GET /api/UserProfile
        """
        try:
            result = await self._get("/api/UserProfile")
            if result.get("success") and result.get("data"):
                return result["data"]
            return None
        except Exception as e:
            logger.error(f"Failed to fetch current user profile: {e}")
            return None
    
    async def property_exists(self, property_id: int) -> Dict[str, Any]:
        """
        Check if a property exists by ID.
        
        GET /api/Property/{propertyId}
        
        Returns:
            Dict with keys: exists (bool), error (str if any)
        """
        try:
            result = await self._get(f"/api/Property/{property_id}")
            if result.get("isSuccess") and result.get("data"):
                return {"exists": True, "error": None}
            elif result.get("isSuccess") is False:
                # Property API returned isSuccess: false
                return {"exists": False, "error": "Property not found"}
            else:
                return {"exists": False, "error": "Invalid API response"}
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {"exists": False, "error": "Property not found"}
            logger.error(f"Failed to check property {property_id}: {e}")
            return {"exists": False, "error": f"API error: {e.response.status_code}"}
        except Exception as e:
            logger.error(f"Failed to check property {property_id}: {e}")
            return {"exists": False, "error": str(e)}


# Singleton instance
_api_client: Optional[PropertyAPIClient] = None


def get_property_api_client(token: Optional[str] = None) -> PropertyAPIClient:
    """Get or create API client instance with optional token.
    
    If token is provided, creates a new instance with that token.
    Otherwise, returns singleton with default token from settings.
    """
    if token:
        return PropertyAPIClient(token=token)
    
    global _api_client
    if _api_client is None:
        _api_client = PropertyAPIClient()
    return _api_client
