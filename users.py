import os
import bcrypt

import chainlit as cl

allowed_users = [user.lower() for user in os.getenv('ALLOWED_USERS', default='admin').split(',')]
enforce_users = os.getenv('ENFORCE_USERS', default=True)

def check_password(password: str, hashed: str) -> bool:
    """Check a password against a stored hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    username_lower = username.lower()

    if enforce_users and not any(user == username_lower for user in allowed_users):
        return None

    if username_lower == "admin" and check_password(password.lower(), os.getenv(username_lower)):
        return cl.User(
            identifier="admin", metadata={"role": "admin", "provider": "credentials"}
        )
    elif check_password(password.lower(), os.getenv(username_lower)):
        return cl.User(
            identifier=username_lower, metadata={"role": "user", "provider": "credentials"}
        )
    else:
        return None

