"""Session helpers."""

from src.auth import tokens


def open_session(user_id):
    return tokens.issue_token(user_id)
