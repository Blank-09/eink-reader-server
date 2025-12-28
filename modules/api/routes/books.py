from fastapi import APIRouter, Query

from modules.kavita.client import kavita_client

router = APIRouter(prefix="/api/books", tags=["books"])


@router.get("/{book_id}/text", response_model=str)
async def get_book_page(book_id: int, page: int = Query(default=0, ge=0)):
    response = await kavita_client.get_book_page(chapter_id=book_id, page=page)
    return response
