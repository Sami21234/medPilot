"""

src/seed_admin.py - one-time script to create first admin (admins aren't self-registered via the public form, on purpose)

"""

"""Creates the first admin account. Run manually: python -m src.seed_admin"""
# from app import create_app
# from src.models import db, User

# app = create_app()

# with app.app_context():
#     email = input("Admin emial: ".strip().lower())
#     if User.query.filter_by(email = email).first():
#         print("An account with this email already exists.")
#     else:
#         name = input("Admin name: ").strip()
#         password = input("Admin password: ").strip()
#         admin = User(name=name, email=email, role="admin")
#         admin.set_password(password)
#         db.session.add(admin)
#         db.session.commit()
#         print(f"Admin account created: {email}")
        
from app import create_app
from src.models import db, User

app = create_app()

def run_seed_admin():
    with app.app_context():
        email = input("Admin email: ").strip().lower()
        if not email:
            print("Email cannot be blank.")
            return

        if User.query.filter_by(email=email).first():
            print("An account with this email already exists.")
        else:
            name = input("Admin name: ").strip()
            password = input("Admin password: ").strip()
            
            if not name or not password:
                print("Name and password cannot be blank.")
                return

            admin = User(name=name, email=email, role="admin")
            admin.set_password(password)
            db.session.add(admin)
            db.session.commit()
            print(f"Admin account created successfully: {email}")

if __name__ == "__main__":
    run_seed_admin()