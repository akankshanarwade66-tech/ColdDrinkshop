# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(500), default='https://via.placeholder.com/300x200?text=No+Image')


from datetime import datetime

class LoginHistory(db.Model):
    id = db.                                                                                                Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    username = db.Column(db.String(150))
    login_time = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150))
    drink_name = db.Column(db.String(100))
    qty = db.Column(db.Integer)
    price = db.Column(db.Float)  # qty*price
    phone = db.Column(db.String(20))
    address = db.Column(db.String(300))
    order_time = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default="Pending")
    payment_mode = db.Column(db.String(50), default="COD")  # Cash on delivery