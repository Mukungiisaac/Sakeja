from sakeja_models import db, User
from werkzeug.security import generate_password_hash
from app import app

with app.app_context():
    admin = User(
        email='admin@sakeja.com',
        name='Admin',
        password=generate_password_hash('adminpass'),
        role='admin',
        is_approved=True
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin created!")
