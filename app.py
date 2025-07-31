from flask import Flask, render_template, redirect, request, url_for, flash
from extensions import db, login_manager
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sakeja_models import User, House
from functools import wraps
import os

# Flask App Setup
app = Flask(__name__)
app.secret_key = 'sakeja-secret-key'

# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sakeja.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File Upload Config
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Restrict access to landlords only
def landlord_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'landlord':
            flash('Access restricted to landlords.')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Home Route
@app.route('/')
def home():
    return redirect(url_for('login'))


# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']

        # ✅ Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email is already registered. Try logging in or use a different email.')
            return redirect(url_for('register'))

        # ✅ If email not taken, proceed to add
        user = User(email=email, name=name, password=password, role=role)
        db.session.add(user)
        db.session.commit()

        flash('Registered successfully! You can now log in.')
        return redirect(url_for('login'))

    return render_template('register.html')


# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Welcome back!')

            # Redirect based on role
            if user.role == 'landlord':
                return redirect(url_for('landlord_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('home'))  # fallback

        flash('Invalid login details')
    return render_template('login.html')


# Dashboard (student or landlord redirect later)
# @app.route('/dashboard')
# @login_required
# def dashboard():
#     return render_template('dashboard.html', user=current_user)

# Logout
@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# -------------------------------
# LANDLORD FEATURES BELOW ⬇️
# -------------------------------

# Landlord Dashboard
@app.route('/landlord/dashboard')
@login_required
@landlord_required
def landlord_dashboard():
    from sakeja_models import House, Booking
    houses = House.query.filter_by(landlord_id=current_user.id).all()

    # Get bookings for landlord's houses
    bookings = Booking.query.join(House).filter(House.landlord_id == current_user.id).all()

    return render_template('landlord_dashboard.html', houses=houses, bookings=bookings)



@app.route('/landlord/edit/<int:house_id>', methods=['GET', 'POST'])
@login_required
@landlord_required
def edit_house(house_id):
    from sakeja_models import House
    house = House.query.get_or_404(house_id)

    if house.landlord_id != current_user.id:
        flash("Unauthorized access.")
        return redirect(url_for('landlord_dashboard'))

    if request.method == 'POST':
        house.title = request.form['title']
        house.location = request.form['location']
        house.rent = request.form['rent']
        house.distance = request.form['distance']
        house.deposit = request.form['deposit']
        house.house_type = request.form['house_type']
        house.water = 'water' in request.form
        house.wifi = 'wifi' in request.form
        house.contact_number = request.form['contact_number']

        photo = request.files['photo']
        if photo and photo.filename:
            filename = secure_filename(photo.filename)
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            house.photo = filename

        db.session.commit()
        flash('House updated successfully!')
        return redirect(url_for('landlord_dashboard'))

    return render_template('edit_house.html', house=house)

@app.route('/landlord/delete/<int:house_id>')
@login_required
@landlord_required
def delete_house(house_id):
    from sakeja_models import House
    house = House.query.get_or_404(house_id)

    if house.landlord_id != current_user.id:
        flash("Unauthorized deletion attempt.")
        return redirect(url_for('landlord_dashboard'))

    db.session.delete(house)
    db.session.commit()
    flash('House deleted successfully.')
    return redirect(url_for('landlord_dashboard'))

# Post a House Route
@app.route('/landlord/post', methods=['GET', 'POST'])
@login_required
@landlord_required
def post_house():
    if request.method == 'POST':
        title = request.form['title']
        location = request.form['location']
        rent = request.form['rent']
        distance = request.form['distance']
        deposit = request.form['deposit']
        house_type = request.form['house_type']
        water = 'water' in request.form
        wifi = 'wifi' in request.form
        contact_number = request.form['contact_number']
        photo = request.files['photo']

        if photo:
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            photo.save(photo_path)

            house = House(
                title=title,
                location=location,
                rent=rent,
                distance=distance,
                deposit=deposit,
                house_type=house_type,
                water=water,
                wifi=wifi,
                photo=filename,
                contact_number=contact_number,
                landlord_id=current_user.id
            )
            db.session.add(house)
            db.session.commit()
            flash('House posted successfully!')
            return redirect(url_for('landlord_dashboard'))
        else:
            flash("Please upload a photo.")

    return render_template('post_house.html')

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    from sakeja_models import House
    houses = House.query.all()
    return render_template('student_dashboard.html', houses=houses)

@app.route('/view_house/<int:house_id>')
@login_required
def view_house(house_id):
    from sakeja_models import House
    house = House.query.get_or_404(house_id)
    return render_template('view_house.html', house=house)

@app.route('/book_house/<int:house_id>', methods=['POST'])
@login_required
def book_house(house_id):
    from sakeja_models import House, Booking
    house = House.query.get_or_404(house_id)

    booking = Booking(
        house_id=house.id,
        student_name=request.form['fullname'],
        student_email=request.form['email'],
        student_phone=request.form['phone'],
        id_number=request.form['id_number'],
        move_in_date=request.form['move_in_date'],
        message=request.form.get('message')
    )

    db.session.add(booking)
    db.session.commit()

    flash('Booking successful! The landlord will contact you soon.', 'success')
    return redirect(url_for('student_dashboard'))

# -------------------------------
# Run App
# -------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
