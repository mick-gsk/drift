"""Token helpers."""


def validate_token(token, audience):
    return bool(token) and bool(audience)


def issue_token(user_id):
    return f"token-{user_id}"
