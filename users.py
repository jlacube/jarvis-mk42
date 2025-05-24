import os
import bcrypt

import chainlit as cl

# List of allowed usernames from environment variable, converted to lowercase
allowed_users = [user.lower() for user in os.getenv('ALLOWED_USERS', default='admin').split(',')]

# Whether to enforce user restrictions (True by default)
enforce_users = os.getenv('ENFORCE_USERS', default=True)

def check_password(password: str, hashed: str) -> bool:
    """
    Verify a password against a stored bcrypt hash.
    
    This function securely compares a plaintext password against a previously
    hashed password using the bcrypt algorithm.
    
    Args:
        password (str): The plaintext password to check
        hashed (str): The bcrypt hash to compare against
        
    Returns:
        bool: True if the password matches the hash, False otherwise
        
    Note:
        This function handles encoding the strings to UTF-8 as required by bcrypt.
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

@cl.password_auth_callback
async def auth_callback(username: str, password: str):
    """
    Authenticate users based on username and password.
    
    This Chainlit callback function verifies user credentials against stored
    password hashes in environment variables. It enforces user restrictions
    if enabled and assigns appropriate roles.
    
    Args:
        username (str): The username provided by the user
        password (str): The password provided by the user
        
    Returns:
        cl.User: A User object with identifier and metadata if authentication succeeds
        None: If authentication fails
        
    Authorization Logic:
        1. Enforces allowed users list if ENFORCE_USERS is True
        2. Checks for admin credentials first
        3. Then checks for regular user credentials
        4. Returns None if no match is found
        
    Note:
        Password hashes should be stored in environment variables named after the username.
    """
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

