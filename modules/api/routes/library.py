from fastapi import APIRouter, HTTPException

from models import LibraryResponse, SeriesResponse
from modules.kavita.client import kavita_client
from utils.logger import get_logger

router = APIRouter(prefix="/api/library", tags=["library"])
logger = get_logger(__name__)


@router.get("/list", response_model=list[LibraryResponse])
async def get_libraries():
    """Get all available libraries from Kavita"""
    try:
        libraries = await kavita_client.get_libraries()
        return libraries
    except Exception as e:
        logger.error(f"Failed to fetch libraries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{library_id}/series/list", response_model=list[SeriesResponse])
async def get_series(library_id: int):
    """Get all series in a library"""
    try:
        series = await kavita_client.get_series(library_id)
        return series
    except Exception as e:
        logger.error(f"Failed to fetch series: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series/{series_id}/details")  # response_model=list[ChapterResponse]
async def get_series_detail(series_id: int):
    try:
        series_details = await kavita_client.get_series_detail(series_id)
        return series_details
    except Exception as e:
        logger.error(f"Failed to fetch chapters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/series/{series_id}/volumes/list")  # response_model=list[ChapterResponse]
async def get_chapters(series_id: int):
    try:
        volumes = await kavita_client.get_series_volumes(series_id)
        return volumes
    except Exception as e:
        logger.error(f"Failed to fetch chapters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
