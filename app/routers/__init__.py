from app.routers.documents import router as documents_router
from app.routers.upload import router as upload_router
from app.routers.folders import router as folders_router
from app.routers.search import router as search_router

router = documents_router
upload = upload_router
folders = folders_router
search = search_router

__all__ = ["router", "documents", "upload", "folders", "search"]
