import hashlib, hmac, secrets, os, sys
import keyring
from fastapi import HTTPException, Header

TOKEN = os.environ.get("AIOS_SESSION_TOKEN") or secrets.token_urlsafe(48)
SERVICE = "AI Company OS"


def authorize(authorization: str = Header(default="")):
    if not hmac.compare_digest(authorization, "Bearer " + TOKEN):
        raise HTTPException(401, "Desktop session required")


def set_secret(name, value):
    if sys.platform != "win32":
        raise HTTPException(
            503, "Credential storage requires Windows Credential Manager"
        )
    from keyring.backends.Windows import WinVaultKeyring

    WinVaultKeyring().set_password(SERVICE, name, value)


def get_secret(name):
    if sys.platform != "win32":
        return None
    from keyring.backends.Windows import WinVaultKeyring

    return WinVaultKeyring().get_password(SERVICE, name)


def delete_secret(name):
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring

        try:
            WinVaultKeyring().delete_password(SERVICE, name)
        except keyring.errors.PasswordDeleteError:
            pass


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    return (
        salt
        + ":"
        + hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
        ).hex()
    )


def verify_password(password, encoded):
    return hmac.compare_digest(password_hash(password, encoded.split(":")[0]), encoded)
