import re
from passlib.context import CryptContext


pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto",
)


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    """Verify a plaintext password against its hash."""
    if not plain_password or not hashed_password:
        return False
    try:
        return pwd_context.verify(
            plain_password,
            hashed_password,
        )
    except Exception:
        return False


def validate_password_complexity(password: str) -> tuple[bool, str | None]:
    """
    Validate enterprise password complexity according to SOC governance requirements:
    1. First character must be a capital letter (A-Z)
    2. Minimum length of 8 characters (max 128)
    3. Contains at least one lowercase letter (a-z)
    4. Contains at least one numeric digit (0-9)
    5. Contains at least one special character / symbol (!@#$%^&* etc.)
    """
    if not password:
        return False, "Password cannot be empty."

    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if len(password) > 128:
        return False, "Password cannot exceed 128 characters."

    # Condition 1: First letter must be Capital
    if not password[0].isupper():
        return False, "First letter of password must be a capital letter (A-Z)."

    # Condition 2: Contains lowercase letter
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter (a-z)."

    # Condition 3: Contains digit
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number (0-9)."

    # Condition 4: Contains special character
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]", password):
        return False, "Password must contain at least one special character (e.g. !@#$%^&*)."

    return True, None
