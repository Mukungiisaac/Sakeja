from extensions import db
from flask_login import UserMixin
from datetime import datetime

# ------------------------
# Item Model
# ------------------------
from extensions import db
class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    photo = db.Column(db.String(100))
    seller_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# ------------------------
# User Model
# ------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # student, landlord, seller, admin
    is_approved = db.Column(db.Boolean, default=False)

    houses = db.relationship('House', backref='landlord', lazy=True)
    items = db.relationship('Item', backref='seller', lazy=True)


# ------------------------
# House Model
# ------------------------
class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    location = db.Column(db.String(100))
    rent = db.Column(db.Float)
    distance = db.Column(db.Float)
    deposit = db.Column(db.Float)
    house_type = db.Column(db.String(50))
    water = db.Column(db.Boolean)
    wifi = db.Column(db.Boolean)
    contact_number = db.Column(db.String(20))
    photo = db.Column(db.String(100))
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'))


# ------------------------
# Booking Model
# ------------------------
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    student_email = db.Column(db.String(100), nullable=False)
    student_phone = db.Column(db.String(20), nullable=False)
    reg_number = db.Column(db.String(20), nullable=False)
    move_in_date = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    house = db.relationship('House', backref='bookings')
