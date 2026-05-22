"""
Create the first admin user.
Usage (inside Docker): docker exec -it <container> python create_admin.py
Usage (local): cd app && python create_admin.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal
from models.user import User, Role
from services.auth import hash_password

db = SessionLocal()

existing = db.query(User).filter(User.username == "admin").first()
if existing:
    print("Admin user already exists!")
    db.close()
    sys.exit(0)

admin = User(
    username="admin",
    email="admin@local.dev",
    hashed_password=hash_password("admin"),
    role=Role.admin,
    display_name="Admin"
)
db.add(admin)
db.commit()
print("✅ Admin created: username=admin  password=admin")
print("⚠️  Change the password after first login!")
db.close()
