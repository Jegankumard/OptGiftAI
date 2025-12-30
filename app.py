import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["OMP_NUM_THREADS"] = "1"
import torch
from recommender import GiftRecommender
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Interaction, PRODUCTS
from models import PRODUCTS
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///optgift.db'

db.init_app(app)
engine = GiftRecommender(PRODUCTS)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# DB setup
with app.app_context():
    db.create_all()

# Routes 
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')
        user = User.query.filter_by(phone=phone).first()
        
        if user and check_password_hash(user.password_hash, password):
            # Simulated OTP Check would go here
            login_user(user)
            # Check if first time user (empty prefs)
            if user.preferences == '{}':
                return redirect(url_for('wizard'))
            return redirect(url_for('dashboard'))
        flash('Invalid phone or password')
    return render_template('login.html')

# Signup route
@app.route('/signup', methods=['POST'])
def signup():
    phone = request.form.get('phone')
    password = request.form.get('password')
    name = request.form.get('name')
    age = request.form.get('age')
    
    if User.query.filter_by(phone=phone).first():
        flash('User already exists')
        return redirect(url_for('login'))
        
    new_user = User(
        phone=phone,
        name=name,
        age=age,
        password_hash=generate_password_hash(password)
    )
    db.session.add(new_user)
    db.session.commit()
    login_user(new_user)
    return redirect(url_for('wizard'))

# Wizard route
@app.route('/wizard', methods=['GET', 'POST'])
@login_required
def wizard():
    if request.method == 'POST':
        prefs = {
            "interests": request.form.getlist('interests'),
            "priority": request.form.get('priority'), # Price vs Quality
            "occasion": request.form.get('occasion_default')
        }
        current_user.preferences = json.dumps(prefs)
        db.session.commit()
        return redirect(url_for('dashboard'))
    return render_template('wizard.html')

# Dashboard route
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # 1. Defaults
    current_mode = 'advanced'
    normal_query = ''
    occasion = ''
    relationship = ''
    likes = ''
    comments = ''
    context_query = "general gifts" 
    
    # Containers for the 3 types of recommendations
    content_recs = []
    collab_recs = []
    hybrid_recs = []
    
    if request.method == 'POST':
        # 2. Capture Inputs
        current_mode = request.form.get('search_mode', 'advanced')
        
        use_personalization = request.form.get('use_personalization')
        personal_tags = ""
        if use_personalization == 'yes' and current_user.preferences:
            try:
                user_prefs = json.loads(current_user.preferences)
                personal_tags = " ".join(user_prefs.get('interests', []))
            except:
                pass

        # 3. Build Query
        if current_mode == 'normal':
            normal_query = request.form.get('normal_query', '')
            if normal_query:
                context_query = f"{normal_query} {personal_tags}".strip()
        else:
            occasion = request.form.get('occasion', '')
            relationship = request.form.get('relationship', '')
            likes = request.form.get('likes', '')
            comments = request.form.get('comments', '')
            
            parts = []
            if occasion: parts.append(f"{occasion}")
            if relationship: parts.append(f"for {relationship}")
            if likes: parts.append(f"loves {likes}")
            if comments: parts.append(f"{comments}")
            if personal_tags: parts.append(f"interests: {personal_tags}")
            if parts:
                context_query = " ".join(parts)
        
        # --- 4. GENERATE 3 DISTINCT LISTS ---
        
        # A. Content-Based (Text Matching)
        content_recs = engine.get_content_based(context_query)
        
        # B. Collaborative (Based on what users clicked/liked in DB)
        # Fetch all interactions from DB to find "Popular" items
        all_interactions = Interaction.query.all()
        collab_recs = engine.get_collaborative_based(all_interactions)
        
        # C. Hybrid (Combination)
        hybrid_recs = engine.get_hybrid_based(context_query)

    # Fallback if page just loaded (GET request)
    if not content_recs:
        content_recs = PRODUCTS[:4]
        collab_recs = PRODUCTS[4:8]
        hybrid_recs = PRODUCTS[8:12]

    try:
        cart_ids = json.loads(current_user.cart) if current_user.cart else []
    except:
        cart_ids = []

    return render_template('dashboard.html', 
                         content_recs=content_recs, 
                         collab_recs=collab_recs,
                         hybrid_recs=hybrid_recs,
                         current_mode=current_mode,
                         normal_query=normal_query,
                         occasion=occasion,
                         relationship=relationship,
                         likes=likes,
                         comments=comments,
                         cart_ids=cart_ids)


    
# Context processor route
@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated and current_user.cart:
        try:
            cart_list = json.loads(current_user.cart)
            return dict(cart_count=len(cart_list))
        except:
            return dict(cart_count=0)
    return dict(cart_count=0)


# Add to cart route
@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    data = request.json
    # FIX: Cast to int to match MOCK_PRODUCTS ID type
    product_id = int(data.get('product_id')) 
    
    try:
        cart_list = json.loads(current_user.cart) if current_user.cart else []
    except:
        cart_list = []

    if product_id not in cart_list:
        cart_list.append(product_id)
        current_user.cart = json.dumps(cart_list)
        db.session.commit()
        return jsonify({"status": "success", "cart_count": len(cart_list), "message": "Item added to cart successfully"})
    
    return jsonify({"status": "exists", "cart_count": len(cart_list), "message": "Item is already in your cart"})

# Remove from cart route
@app.route('/remove_from_cart', methods=['POST'])
@login_required
def remove_from_cart():
    data = request.json
    product_id = int(data.get('product_id'))
    
    try:
        cart_list = json.loads(current_user.cart) if current_user.cart else []
    except:
        cart_list = []

    if product_id in cart_list:
        cart_list.remove(product_id)
        current_user.cart = json.dumps(cart_list)
        db.session.commit()
    
    return jsonify({"status": "success", "cart_count": len(cart_list)})

# Cart route
@app.route('/cart')
@login_required
def view_cart():
    try:
        cart_ids = json.loads(current_user.cart) if current_user.cart else []
    except:
        cart_ids = []
    
    # CHANGED: Filter PRODUCTS
    cart_items = [p for p in PRODUCTS if p['id'] in cart_ids]
    
    total_price = sum(item['price'] for item in cart_items)
    
    return render_template('cart.html', cart_items=cart_items, total=total_price)


# Get replacement card route
@app.route('/get_replacement_card', methods=['POST'])
@login_required
def get_replacement_card():
    data = request.json
    exclude_ids = data.get('exclude_ids', [])
    
    # CHANGED: Use PRODUCTS
    new_prod = next((p for p in PRODUCTS if p['id'] not in exclude_ids), None)
    
    if new_prod:
        try:
            cart_ids = json.loads(current_user.cart) if current_user.cart else []
        except:
            cart_ids = []
            
        html = render_template('product_card.html', prod=new_prod, cart_ids=cart_ids)
        return jsonify({"status": "success", "html": html})
    
    return jsonify({"status": "no_more", "message": "No more items"})

# Feedback route
@app.route('/feedback', methods=['POST'])
@login_required
def feedback():
    data = request.json
    product_id = data.get('product_id')
    action = data.get('action') 
    
    # CHANGED: Use PRODUCTS
    prod = next((p for p in PRODUCTS if p['id'] == product_id), None)
    
    if prod:
        new_weights = engine.update_rl_weights(current_user.rl_weights, action, prod['price'])
        current_user.rl_weights = new_weights
        
        interaction = Interaction(user_id=current_user.id, product_id=str(product_id), action_type=action)
        db.session.add(interaction)
        db.session.commit()
        
        return jsonify({"status": "success", "new_weights": new_weights})
    
    return jsonify({"status": "error", "message": "Product not found"})

# Profile route
@app.route('/profile')
@login_required
def profile():
    # Convert stored JSON string back to Python Dictionary to display
    user_prefs = json.loads(current_user.preferences) if current_user.preferences else {}
    return render_template('profile.html', user=current_user, prefs=user_prefs)


# Update preferences route
@app.route('/update_preferences', methods=['GET', 'POST'])
@login_required
def update_preferences():
    # Load current prefs to pre-fill the form
    current_prefs = json.loads(current_user.preferences) if current_user.preferences else {}
    
    if request.method == 'POST':
        new_prefs = {
            "interests": request.form.getlist('interests'),
            "priority": request.form.get('priority'),
            "occasion": request.form.get('occasion_default')
        }
        current_user.preferences = json.dumps(new_prefs)
        db.session.commit()
        flash('Preferences updated successfully!')
        return redirect(url_for('profile'))
        
    return render_template('update_preferences.html', prefs=current_prefs)

# Logout route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))

# main function
if __name__ == '__main__':
    app.run(debug=True)