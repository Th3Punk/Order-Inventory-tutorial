from pymongo import MongoClient

from app.core.config import settings

_client: MongoClient | None = None


def get_mongo_client() -> MongoClient:
    global _client
    if _client is None:
        if not settings.mongo_url:
            raise ValueError("MONGO_URL is not configured")
        _client = MongoClient(settings.mongo_url)
    return _client
