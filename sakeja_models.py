from extensions import db
from flask_login import UserMixin

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100))

    houses = db.relationship('House', backref='landlord', lazy=True)


class House(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120))
    location = db.Column(db.String(120))
    rent = db.Column(db.Float)
    distance = db.Column(db.Float)
    deposit = db.Column(db.Float, nullable=True)
    house_type = db.Column(db.String(50))  # e.g. Single, Bedsitter, 1 Bedroom
    water = db.Column(db.Boolean, default=False)
    wifi = db.Column(db.Boolean, default=False)
    photo = db.Column(db.String(255))
    contact_number = db.Column(db.String(20))
    landlord_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
from datetime import datetime
from extensions import db

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    house_id = db.Column(db.Integer, db.ForeignKey('house.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    student_email = db.Column(db.String(100), nullable=False)
    student_phone = db.Column(db.String(20), nullable=False)
    id_number = db.Column(db.String(20), nullable=False)
    move_in_date = db.Column(db.String(20), nullable=False)
    message = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    house = db.relationship('House', backref='bookings')
