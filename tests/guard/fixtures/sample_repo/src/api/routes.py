"""HTTP routes."""

from src.services import user_service


def get_user(user_id):
    return user_service.load_user(user_id)
