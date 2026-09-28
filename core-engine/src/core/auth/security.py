from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def normalize_email(email: str) -> str:
    """Mismo criterio en cualquier punto que compare o busque por email
    (login, recuperacion): sin esto, `authenticate_user` comparaba el email
    tal cual llegaba del formulario mientras `complete_recovery` ya
    normalizaba -- un espacio o una mayuscula de mas en el login hacia fallar
    la autenticacion aunque la contrasena fuera correcta. Hallazgo real,
    2026-09-28 (login en 401 justo tras una recuperacion exitosa)."""
    return email.strip().casefold()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
