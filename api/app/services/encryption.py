"""Token encryption utilities using Fernet (AES)."""
from cryptography.fernet import Fernet
import base64
import hashlib
from app.config import get_settings


def get_fernet() -> Fernet:
    """Get Fernet instance with encryption key from settings."""
    settings = get_settings()
    # Convert hex key to bytes and derive a proper Fernet key
    # Key must be a valid hex string (0-9, a-f only), 64+ hex chars = 32+ bytes
    try:
        key_bytes = bytes.fromhex(settings.encryption_key)
    except ValueError as e:
        raise ValueError(
            "ENCRYPTION_KEY must be a valid hex string (0-9, a-f). "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        ) from e
    if len(key_bytes) < 32:
        raise ValueError("ENCRYPTION_KEY must be at least 64 hex characters (32 bytes)")
    # Use first 32 bytes and base64 encode for Fernet
    fernet_key = base64.urlsafe_b64encode(key_bytes[:32])
    return Fernet(fernet_key)


def encrypt_token(token: str) -> str:
    """Encrypt a token string."""
    fernet = get_fernet()
    encrypted = fernet.encrypt(token.encode())
    return encrypted.decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token string."""
    fernet = get_fernet()
    decrypted = fernet.decrypt(encrypted_token.encode())
    return decrypted.decode()
