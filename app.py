from flask import Flask, render_template, redirect, request, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_migrate import Migrate
from functools import wraps
import os

from extensions import db, login_manager
from sakeja_models import User, House, Item

# -------------------------------
# App Initialization
# -------------------------------
app = Flask(__name__)
app.secret_key = 'sakeja-secret-key'

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sakeja.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File Upload Config
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate = Migrate(app, db)

# -------------------------------
# Login Manager Setup
# -------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------------------
# Custom Role Decorators
# -------------------------------
def landlord_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'landlord':
            flash('Access restricted to landlords.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# -------------------------------
# Routes
# -------------------------------

@app.route('/')
def home():
    return redirect(url_for('student_dashboard'))

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        if User.query.filter_by(email=email).first():
            flash('Email already registered.')
            return redirect(url_for('register'))

        is_approved = True if role == 'student' else False
        new_user = User(email=email, name=name, password=password, role=role, is_approved=is_approved)
        db.session.add(new_user)
        db.session.commit()

        flash('Registered successfully! You can now log in.')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Welcome back!')

            # Redirect by role
            return redirect(url_for('seller_dashboard')) if user.role == 'seller' else redirect(url_for(f"{user.role}_dashboard"))

        flash('Invalid credentials.')
    return render_template('login.html')

# Logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# -------------------------------
# LANDLORD FEATURES
# -------------------------------

@app.route('/landlord/dashboard')
@login_required
@landlord_required
def landlord_dashboard():
    from sakeja_models import Booking
    houses = House.query.filter_by(landlord_id=current_user.id).all()
    bookings = Booking.query.join(House).filter(House.landlord_id == current_user.id).all()
    return render_template('landlord_dashboard.html', houses=houses, bookings=bookings)

@app.route('/landlord/post', methods=['GET', 'POST'])
@login_required
@landlord_required
def post_house():
    if not current_user.is_approved:
        flash('Admin approval required to post houses.')
        return redirect(url_for('landlord_dashboard'))

    if request.method == 'POST':
        house = House(
            title=request.form['title'],
            location=request.form['location'],
            rent=request.form['rent'],
            distance=request.form['distance'],
            deposit=request.form['deposit'],
            house_type=request.form['house_type'],
            water='water' in request.form,
            wifi='wifi' in request.form,
            contact_number=request.form['contact_number'],
            landlord_id=current_user.id
        )

        photo = request.files['photo']
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            house.photo = filename

        db.session.add(house)
        db.session.commit()
        flash('House posted successfully!')
        return redirect(url_for('landlord_dashboard'))

    return render_template('post_house.html')

@app.route('/landlord/edit/<int:house_id>', methods=['GET', 'POST'])
@login_required
@landlord_required
def edit_house(house_id):
    house = House.query.get_or_404(house_id)

    if house.landlord_id != current_user.id:
        flash('Unauthorized access.')
        return redirect(url_for('landlord_dashboard'))

    if request.method == 'POST':
        for field in ['title', 'location', 'rent', 'distance', 'deposit', 'house_type', 'contact_number']:
            setattr(house, field, request.form[field])
        house.water = 'water' in request.form
        house.wifi = 'wifi' in request.form

        photo = request.files['photo']
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            house.photo = filename

        db.session.commit()
        flash('House updated.')
        return redirect(url_for('landlord_dashboard'))

    return render_template('edit_house.html', house=house)

@app.route('/landlord/delete/<int:house_id>')
@login_required
@landlord_required
def delete_house(house_id):
    house = House.query.get_or_404(house_id)
    if house.landlord_id != current_user.id:
        flash('Unauthorized deletion.')
        return redirect(url_for('landlord_dashboard'))

    db.session.delete(house)
    db.session.commit()
    flash('House deleted.')
    return redirect(url_for('landlord_dashboard'))

# -------------------------------
# SELLER FEATURES
# -------------------------------

# -------------------------------
# SELLER FEATURES
# -------------------------------

@app.route('/seller/marketplace', methods=['GET', 'POST'])
@login_required
def seller_marketplace():
    if current_user.role != 'seller':
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    if not current_user.is_approved:
        flash('You are not approved to post items yet. Please wait for admin approval.')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        price = request.form['price']
        phone = request.form['phone']
        location = request.form['location']
        photo = request.files['photo']

        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

            item = Item(
                title=title,
                description=description,
                price=price,
                phone=phone,
                location=location,
                photo=filename,
                seller_id=current_user.id
            )
            db.session.add(item)
            db.session.commit()
            flash('Item posted successfully!')

            # ✅ Redirect to seller dashboard after posting
            return redirect(url_for('seller_dashboard'))
        else:
            flash('Please upload a photo.')

    # Just render a form for posting items
    return render_template('post_item.html')  


@app.route('/seller/dashboard')
@login_required
def seller_dashboard():
    if current_user.role != 'seller':
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    # Show only the seller's own items
    items = Item.query.filter_by(seller_id=current_user.id).all()
    return render_template('seller_dashboard.html', items=items)

@app.route('/marketplace')
@login_required
def marketplace():
    items = Item.query.all()
    return render_template('marketplace.html', items=items)

# -------------------------------
# STUDENT FEATURES
# -------------------------------

@app.route('/student/dashboard')
def student_dashboard():
    from sakeja_models import House, Item

    houses = House.query.all()
    items = Item.query.all()  # ✅ Fetch all posted items

    return render_template('student_dashboard.html', houses=houses, items=items)


@app.route('/view_house/<int:house_id>')
@login_required
def view_house(house_id):
    house = House.query.get_or_404(house_id)
    return render_template('view_house.html', house=house)

@app.route('/book_house/<int:house_id>', methods=['POST'])
@login_required
def book_house(house_id):
    from sakeja_models import Booking
    booking = Booking(
        house_id=house_id,
        student_name=request.form['fullname'],
        student_email=request.form['email'],
        student_phone=request.form['phone'],
        reg_number=request.form['reg_number'],
        move_in_date=request.form['move_in_date'],
        message=request.form.get('message')
    )
    db.session.add(booking)
    db.session.commit()
    flash('Booking successful!')
    return redirect(url_for('student_dashboard'))

# -------------------------------
# ADMIN FEATURES
# -------------------------------

# -------------------------------
# ADMIN FEATURES
# -------------------------------

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    pending_landlords = User.query.filter_by(role='landlord', is_approved=False).all()
    pending_sellers = User.query.filter_by(role='seller', is_approved=False).all()
    landlords = User.query.filter_by(role='landlord', is_approved=True).all()
    sellers = User.query.filter_by(role='seller', is_approved=True).all()
    students = User.query.filter_by(role='student').all()

    return render_template(
        'admin_dashboard.html',
        pending_landlords=pending_landlords,
        pending_sellers=pending_sellers,
        landlords=landlords,
        sellers=sellers,   # ✅ Pass approved sellers too
        students=students
    )



@app.route('/admin/approve/<int:user_id>')
@login_required
def approve_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f'{user.role.capitalize()} approved.')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/reject/<int:user_id>')
@login_required
def reject_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'{user.role.capitalize()} rejected.')
    return redirect(url_for('admin_dashboard'))

    # Override root to go to student dashboard when app starts
    @app.route('/')
    def home_override():
        return redirect(url_for('student_dashboard'))
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'{user.role.capitalize()} rejected.')
    return redirect(url_for('admin_dashboard'))

# Universal role router
@app.route('/dashboard')
@login_required
def dashboard():
    role_routes = {
        'landlord': 'landlord_dashboard',
        'seller': 'seller_dashboard',
        'student': 'student_dashboard',
        'admin': 'admin_dashboard'
    }
    route = role_routes.get(current_user.role)
    return redirect(url_for(route)) if route else redirect(url_for('home'))

@app.route('/homepage')
@login_required
def homepage():
    # Pass your stats here if needed
    return render_template('homepage.html', listings=184, users=461)


@app.route('/revoke_user/<int:user_id>')
@login_required
def revoke_user(user_id):
    if current_user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    user = User.query.get_or_404(user_id)
    
    if user.role in ['landlord', 'seller'] and user.is_approved:
        user.is_approved = False   # ✅ Revoke approval
        db.session.commit()
        flash(f"{user.role.capitalize()} '{user.name}' has been revoked.")
    else:
        flash("Invalid revoke operation.")

    return redirect(url_for('admin_dashboard'))


# -------------------------------
# Run Server
# -------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
