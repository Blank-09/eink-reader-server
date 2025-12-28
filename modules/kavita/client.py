"""
Kavita API Client Module (modules/kavita/client.py)
Handles authentication and data fetching from Kavita server
"""

import httpx

from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from config import settings
from utils.logger import get_logger

logger = get_logger(__name__)


class KavitaConfig(BaseModel):
    base_url: str = "http://localhost:5000"
    api_key: str
    plugin_name: str = "ESP32Reader"


class KavitaClient:
    def __init__(self, config: KavitaConfig):
        self.config = config
        self.base_url = config.base_url.rstrip("/")
        self.token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None
        self.client = httpx.AsyncClient(timeout=30.0)

    async def authenticate(self) -> bool:
        """Authenticate with Kavita server using API key"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/Plugin/authenticate",
                params={"apiKey": self.config.api_key, "pluginName": self.config.plugin_name},
            )
            response.raise_for_status()
            data = response.json()

            # Store token and user info from actual response structure
            self.token = data.get("token")
            self.refresh_token = data.get("refreshToken")

            # Store user information
            self.user_info = {
                "username": data.get("username"),
                "email": data.get("email"),
                "ageRestriction": data.get("ageRestriction"),
                "apiKey": data.get("apiKey"),
                "kavitaVersion": data.get("kavitaVersion"),
            }

            if self.token:
                logger.info(
                    f"Successfully authenticated as: {self.user_info['username']} "
                    f"(Kavita v{self.user_info['kavitaVersion']})"
                )
                return True

            logger.error("No token received from authentication")
            return False

        except httpx.HTTPStatusError as e:
            logger.error(
                f"Authentication failed with status {e.response.status_code}: {e.response.text}"
            )
            return False
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers"""
        if not self.token:
            raise ValueError("Not authenticated. Call authenticate() first.")
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    async def get_libraries(self) -> List[Dict[str, Any]]:
        """Get all libraries"""
        response = await self.client.get(
            f"{self.base_url}/api/Library/libraries", headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def get_series(self, library_id: int) -> List[Dict[str, Any]]:
        """Get all series in a library"""
        response = await self.client.post(
            f"{self.base_url}/api/Series/v2",
            json={
                "statements": [{"field": 19, "value": str(library_id), "comparison": 0}],
                "combination": 1,
                "limitTo": 0,
                "sortOptions": {"isAscending": True, "sortField": 1},
            },
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def get_series_detail(self, series_id: int) -> Dict[str, Any]:
        """Get detailed information about a series"""
        response = await self.client.get(
            f"{self.base_url}/api/Series/{series_id}", headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

    async def get_series_volumes(self, series_id: int) -> List[Dict[str, Any]]:
        """Get detailed information about a series"""
        response = await self.client.get(
            f"{self.base_url}/api/series/series-detail?seriesId={series_id}",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        results = response.json()

        all_volumes = []
        for volume in results["volumes"]:
            all_volumes.append(
                {
                    "id": volume["id"],
                    "name": volume["name"],
                    "pages": volume["pages"],
                    "seriesId": volume["seriesId"],
                    "chapterId": volume["chapters"][0]["id"],
                }
            )

        return all_volumes

    async def get_book_page(self, chapter_id: int, page: int) -> str:
        """Get detailed information about a series"""
        response = await self.client.get(
            f"{self.base_url}/api/book/{chapter_id}/book-page?page={page}",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.text

    async def get_volumes(self, series_id: int) -> List[Dict[str, Any]]:
        """Get all volumes for a series"""
        response = await self.client.get(
            f"{self.base_url}/api/Series/volumes",
            params={"seriesId": series_id},
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def get_chapter_metadata(self, chapter_id: int) -> Dict[str, Any]:
        """Get chapter metadata"""
        response = await self.client.get(
            f"{self.base_url}/api/Reader/chapter-info",
            params={"chapterId": chapter_id},
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def get_book_resources(self, chapter_id: int) -> Dict[str, Any]:
        """Get book resources (for EPUB/PDF chapters)"""
        response = await self.client.get(
            f"{self.base_url}/api/Book/{chapter_id}/book-resources",
            headers=self._get_headers(),
        )
        response.raise_for_status()
        print(response.content)
        return response.json()

    async def download_chapter_page(self, chapter_id: int, page: int) -> bytes:
        """Download a specific page from a chapter (for image-based formats)"""
        response = await self.client.get(
            f"{self.base_url}/api/Reader/image",
            params={
                "chapterId": chapter_id,
                "page": page,
                "apiKey": self.user_info.get("apiKey", ""),
                "extractPdf": False,
            },
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.content

    async def get_bookmark(self, chapter_id: int) -> Dict[str, Any]:
        """Get bookmark/reading progress for a chapter"""
        response = await self.client.get(
            f"{self.base_url}/api/Reader/get-progress",
            params={"chapterId": chapter_id},
            headers=self._get_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def mark_chapter_as_read(self, chapter_id: int) -> bool:
        """Mark a chapter as read"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/Reader/mark-read",
                params={"chapterId": chapter_id},
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to mark chapter as read: {e}")
            return False

    async def save_progress(
        self, chapter_id: int, page_num: int, volume_id: int, series_id: int, library_id: int
    ) -> bool:
        """Save reading progress"""
        try:
            response = await self.client.post(
                f"{self.base_url}/api/Reader/progress",
                json={
                    "chapterId": chapter_id,
                    "pageNum": page_num,
                    "volumeId": volume_id,
                    "seriesId": series_id,
                    "libraryId": library_id,
                },
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to save progress: {e}")
            return False

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()


config = KavitaConfig(
    base_url=settings.kavita_base_url,
    api_key=settings.kavita_api_key,
    plugin_name=settings.kavita_plugin_name,
)

kavita_client = KavitaClient(config)


async def connect_kavita_server():
    # Authenticate with Kavita
    auth_success = await kavita_client.authenticate()
    if not auth_success:
        logger.error("Failed to authenticate with Kavita server")
    else:
        logger.info("Successfully authenticated with Kavita server")
