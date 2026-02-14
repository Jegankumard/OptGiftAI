from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json
import pandas as pd
import os

db = SQLAlchemy()

# --- User Model (SQL) ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(20), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    age = db.Column(db.Integer)
    preferences = db.Column(db.Text, default='{}') 
    cart = db.Column(db.Text, default='[]')
    orders = db.Column(db.Text, default='[]')
    rl_weights = db.Column(db.Text, default=json.dumps({
        'price_weight': 0.3, 
        'relevance_weight': 0.7,
        'novelty_weight': 0.1
    }))

# --- Interaction/Feedback Model ---
class Interaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.String(50)) 
    action_type = db.Column(db.String(20)) 
    rating = db.Column(db.Integer, nullable=True) 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# --- Load Products from CSV ---
def load_products_from_csv():
    csv_file = 'optgiftai_database.csv'
    
    if not os.path.exists(csv_file):
        print(f"WARNING: {csv_file} not found. Returning empty list.")
        return []

    try:
        df = pd.read_csv('optgiftai_database.csv')
        products = []
        for _, row in df.iterrows():
            products.append({
                "id": int(row['id']) if pd.notna(row['id']) else 0,
                "title": row['title'] if pd.notna(row['title']) else "Unknown Product",
                "rating": float(row['rating']) if pd.notna(row['rating']) else 0.0,  # Ensure this is added
                "tags": str(row['tags']).split(', ') if pd.notna(row['tags']) else [],
                "price": float(row['price']) if pd.notna(row['price']) else 0.0,
                "description": row['description'] if pd.notna(row['description']) else "",
                "image_url": row['image_url'] if pd.notna(row['image_url']) else "",
                "vendor": row['vendor'] if pd.notna(row['vendor']) else "Unknown",
                "link": row['link'] if pd.notna(row['link']) else "#"
            })
        return products

    except Exception as e:
        # The SyntaxError was likely due to a missing '}' or ')' above this line
        print(f"Error loading product database: {e}")
        return []

# Export the loaded products for app.py and recommender.py
PRODUCTS = load_products_from_csv()