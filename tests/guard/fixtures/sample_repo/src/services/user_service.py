"""Service layer between API and DB."""

from src.db import models


def load_user(user_id):
    return models.fetch_user_row(user_id)
