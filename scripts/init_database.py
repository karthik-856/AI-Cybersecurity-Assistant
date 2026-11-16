"""Apply migrations, seed roles, and optionally create the first administrator."""
import argparse
import getpass

from alembic import command
from alembic.config import Config
from sqlalchemy import select

from backend.app.database.session import SessionLocal
from backend.app.models import Role, User
from backend.app.security.password import hash_password, validate_password_complexity


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admin-username")
    parser.add_argument("--admin-email")
    args = parser.parse_args()
    if bool(args.admin_username) != bool(args.admin_email):
        parser.error("Supply both --admin-username and --admin-email.")
    command.upgrade(Config("alembic.ini"), "head")
    with SessionLocal() as db:
        for name in ("ADMIN", "SOC_ANALYST", "VIEWER"):
            if db.scalar(select(Role).where(Role.name == name)) is None:
                db.add(Role(name=name))
        db.flush()
        if args.admin_username:
            if db.scalar(select(User).where(User.username == args.admin_username)):
                parser.error("That username already exists; no account was changed.")
            password = getpass.getpass("New administrator password: ")
            valid, error = validate_password_complexity(password)
            if not valid:
                parser.error(error)
            if password != getpass.getpass("Confirm password: "):
                parser.error("Passwords do not match.")
            role = db.scalar(select(Role).where(Role.name == "ADMIN"))
            db.add(User(username=args.admin_username, email=args.admin_email,
                        hashed_password=hash_password(password), role_id=role.id, is_active=True))
        db.commit()
    print("Database migrations and roles are ready.")


if __name__ == "__main__":
    main()
