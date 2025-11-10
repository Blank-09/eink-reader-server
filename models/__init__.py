"""
Pydantic Models for API responses
"""

from pydantic import BaseModel
from typing import Optional
from enum import Enum


class ImageFormat(str, Enum):
    """Supported image output formats"""

    PNG = "png"
    BMP = "bmp"


class LibraryResponse(BaseModel):
    """Kavita library response model"""

    id: int
    name: str
    type: Optional[int] = None
    coverImage: Optional[str] = None


class SeriesResponse(BaseModel):
    """Kavita series response model"""

    id: int
    name: str
    localizedName: Optional[str] = None
    originalName: Optional[str] = None
    summary: Optional[str] = None
    coverImage: Optional[str] = None
    pages: Optional[int] = None
    pagesRead: Optional[int] = None


class ChapterResponse(BaseModel):
    """Kavita chapter response model"""

    id: int
    title: Optional[str] = None
    number: str
    volumeId: int
    pages: int
    isSpecial: Optional[bool] = False
    coverImage: Optional[str] = None


class ImageResponse(BaseModel):
    """Response for hex-encoded images"""

    hex: str
    width: int
    height: int
