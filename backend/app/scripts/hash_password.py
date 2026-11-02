"""Generate a bcrypt hash for ADMIN_PASSWORD_HASH.   python -m app.scripts.hash_password"""
import getpass

from app.services.auth import hash_password

if __name__ == "__main__":
    pw = getpass.getpass("Admin password: ")
    if len(pw) < 10:
        raise SystemExit("Use at least 10 characters.")
    print("\nAdd this to your .env (single quotes keep the $ characters safe):")
    print(f"ADMIN_PASSWORD_HASH='{hash_password(pw)}'")
