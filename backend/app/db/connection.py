"""
MongoDB connection management via PyMongo.
"""

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

from backend.app.core.config import settings

# Module-level client – created once, reused everywhere.
client: MongoClient = MongoClient(settings.MONGODB_URI)
db = client["lumberfi"]


def get_db():
    """FastAPI dependency returning the application database."""
    return db


def ping_mongodb() -> bool:
    """
    Send a ping command to MongoDB.

    Returns True if the server responds, False otherwise.
    """
    try:
        client.admin.command("ping")
        return True
    except ConnectionFailure:
        return False
