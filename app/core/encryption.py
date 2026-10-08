"""
Encryption utilities for storing sensitive credentials.

Uses AES-256-GCM for authenticated encryption of API keys and secrets.
"""
import os
import base64
import hashlib
from typing import Tuple, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionError(Exception):
    """Raised when encryption or decryption fails."""
    pass


class CredentialEncryption:
    """
    AES-256-GCM encryption for storing retrievable secrets.

    Uses ENCRYPTION_KEY from environment (or derives from SECRET_KEY).
    """

    def __init__(self, key: Optional[bytes] = None):
        """
        Initialize with an encryption key.

        Args:
            key: 32-byte key. If not provided, derives from environment.
        """
        if key:
            self._key = key
        else:
            self._key = self._get_key_from_env()

    def _get_key_from_env(self) -> bytes:
        """Get or derive a 32-byte encryption key from environment."""
        # Prefer dedicated ENCRYPTION_KEY
        env_key = os.getenv("ENCRYPTION_KEY")
        if env_key:
            # If it's hex-encoded (64 chars = 32 bytes)
            if len(env_key) == 64:
                try:
                    return bytes.fromhex(env_key)
                except ValueError:
                    pass
            # Otherwise derive from it
            return hashlib.sha256(env_key.encode()).digest()

        # Fall back to deriving from SECRET_KEY (env var)
        secret_key = os.getenv("SECRET_KEY")
        if secret_key:
            return hashlib.sha256(secret_key.encode()).digest()

        # Fall back to Flask app config (covers testing where SECRET_KEY
        # is set as a class attribute rather than an environment variable)
        try:
            from flask import current_app
            app_secret = current_app.config.get("SECRET_KEY")
            if app_secret:
                return hashlib.sha256(app_secret.encode()).digest()
        except (ImportError, RuntimeError):
            pass

        raise EncryptionError(
            "No encryption key available. Set ENCRYPTION_KEY or SECRET_KEY environment variable."
        )

    def encrypt(self, plaintext: str) -> Tuple[str, str]:
        """
        Encrypt a string using AES-256-GCM.

        Args:
            plaintext: The string to encrypt

        Returns:
            Tuple of (ciphertext_base64, nonce_base64)
        """
        if not plaintext:
            raise EncryptionError("Cannot encrypt empty string")

        try:
            aesgcm = AESGCM(self._key)
            nonce = os.urandom(12)  # 96-bit nonce for GCM
            ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

            return (
                base64.b64encode(ciphertext).decode('utf-8'),
                base64.b64encode(nonce).decode('utf-8')
            )
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")

    def decrypt(self, ciphertext_b64: str, nonce_b64: str) -> str:
        """
        Decrypt a string using AES-256-GCM.

        Args:
            ciphertext_b64: Base64-encoded ciphertext
            nonce_b64: Base64-encoded nonce

        Returns:
            Decrypted plaintext string
        """
        if not ciphertext_b64 or not nonce_b64:
            raise EncryptionError("Missing ciphertext or nonce")

        try:
            aesgcm = AESGCM(self._key)
            ciphertext = base64.b64decode(ciphertext_b64)
            nonce = base64.b64decode(nonce_b64)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            return plaintext.decode('utf-8')
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")


# Module-level instance for convenience
_encryption: Optional[CredentialEncryption] = None


def get_encryption() -> CredentialEncryption:
    """Get the module-level encryption instance."""
    global _encryption
    if _encryption is None:
        _encryption = CredentialEncryption()
    return _encryption


def encrypt_credential(plaintext: str) -> Tuple[str, str]:
    """Encrypt a credential string. Returns (ciphertext_b64, nonce_b64)."""
    return get_encryption().encrypt(plaintext)


def decrypt_credential(ciphertext_b64: str, nonce_b64: str) -> str:
    """Decrypt a credential string."""
    return get_encryption().decrypt(ciphertext_b64, nonce_b64)
