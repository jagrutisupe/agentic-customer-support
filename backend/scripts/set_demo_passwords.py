from app.auth import hash_password
from app.database.connection import SessionLocal
from app.database.models import User


DEMO_USERS = [
    {
        "name": "Aarav Sharma",
        "email": "aarav@example.com",
        "password": "customer123",
        "role": "customer",
    },
    {
        "name": "Priya Patil",
        "email": "priya@example.com",
        "password": "customer123",
        "role": "customer",
    },
    {
        "name": "Rahul Deshmukh",
        "email": "rahul@example.com",
        "password": "customer123",
        "role": "customer",
    },
    {
        "name": "Sneha Kulkarni",
        "email": "sneha@example.com",
        "password": "customer123",
        "role": "customer",
    },
    {
        "name": "Support Agent",
        "email": "agent@support.local",
        "password": "agent123",
        "role": "support_agent",
    },
    {
        "name": "Admin Support",
        "email": "admin@support.local",
        "password": "admin123",
        "role": "admin",
    },
]


def setup_demo_users():
    db = SessionLocal()
    try:
        for data in DEMO_USERS:
            user = db.query(User).filter(User.email == data["email"]).first()

            if user is None:
                user = User(
                    name=data["name"],
                    email=data["email"],
                    password_hash=hash_password(data["password"]),
                    role=data["role"],
                    is_active=True,
                )
                db.add(user)
                print(f"Created {data['role']}: {data['email']}")
            else:
                user.password_hash = hash_password(data["password"])
                user.role = data["role"]
                user.is_active = True
                print(f"Updated {data['role']}: {data['email']}")

        db.commit()
        print("\nDemo RBAC users are ready.")
    finally:
        db.close()


if __name__ == "__main__":
    setup_demo_users()
