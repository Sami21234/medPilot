from functools import wraps     # used for decorators -> (for example @token_required) for authentication
from flask import Blueprint, request, redirect, url_for, flash, abort       # used for routing and handling HTTP requests
from flask_login import LoginManager, login_user, logout_user, current_user, login_required     # used for user session management and authentication
from src.models import User, db, Doctor, Patient     # used for database models and database session management

auth_bp = Blueprint('auth', __name__)     # create a blueprint for authentication routes
login_manager = LoginManager()     # create a login manager instance for handling user sessions
login_manager.login_view = 'auth.login'     # set the login view for the login manager

def init_auth(app):
    login_manager.init_app(app)     # initialize the login manager with the Flask app

@login_manager.user_loader      # decorator to specify the function that loads a user from the database
def load_user(user_id):
    return User.query.get(int(user_id))     # load the user from the database using the user ID

def role_required(role):
    """
    Decorator enforcing server-side role checks -- a patient token/session
    can NEVER reach a doctor route, even if they guess the URL. This is the
    architecture doc's Section 4 requirement made concrete.
    """
    def decorator(view_func):       # decorator function that takes the original view function as an argument
        @wraps(view_func)
        def wrapped(*args, **kwargs):       # args and kwargs are used to pass any arguments to the original function
            if not current_user.is_authenticated:     # check if the user is authenticated
                return redirect(url_for('auth.login'))     # redirect to login page if not authenticated
            if current_user.role != role:     # check if the user has the required role
                abort(403)     # return a 403 Forbidden error if the user does not have the required role
            return view_func(*args, **kwargs)     # call the original function if the user has the required role
        return wrapped
    return decorator

@auth_bp.route("/register", methods=["POST"])     # route for user registration, accepts POST requests(post method is used to send data to the server)
def register():
    data = request.form     # get the form data from the request
    name = data.get("name", "").strip()     # get the name from the form data
    email = data.get("email", "").strip().lower()     # get the email from the form data
    password = data.get("password", "")     # get the password from the form
    role = data.get("role", "patient")    # get the role from the form data

    if not name or not email or not password:     # check if any of the required fields are missing
        flash("All fields are required.")     # flash an error message if any required field is missing
        return redirect(url_for("index"))     # redirect to the index page

    if role not in ["doctor", "patient"]:     # check if the role is valid
        flash("Invalid role specified.")     # flash an error message if the role is invalid
        return redirect(url_for("index"))     # redirect to the index page

    if User.query.filter_by(email=email).first():     # check if the email is already registered
        flash("An account with this email already exists.")     # flash an error message if the email is already registered
        return redirect(url_for("index"))     # redirect to the index page

    user = User(name=name, email=email, role=role)     # create a new user instance
    user.set_password(password)     # set the password for the user
    db.session.add(user)     # add the user to the database session
    db.session.flush()     # get user.id before committing, to create the role-specific row

    if role == "patient":     # if the role is patient, create a new patient instance
        patient = Patient(user_id=user.id, age = data.get("age"), gender=data.get("gender"))     # create a new patient instance with the user ID and additional patient information
        db.session.add(patient)     # add the patient to the database session
    else:
        # Doctor accounts start UNVERIFIED -- someone (e.g. an admin process)
        # must verify the license before the doctor portal is usable.
        # See architecture.md Section 4
        db.session.add(Doctor(
            user_id=user.id,
            specialization=data.get("specialization", ""),
            license_number=data.get("license_number", ""), 
            is_verified=False,
        ))     # add the doctor to the database session with verified set to False

    db.session.commit()     # commit the changes to the database
    login_user(user)     # log in the user after registration
    # return redirect(url_for("patient.dashboard" if role == "patient" else "doctor.dashboard"))     # redirect to the appropriate dashboard based on the user's role
    # Redirect based on user role
    if user.role == "patient":
        return redirect(url_for("patient.dashboard"))
    elif user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    else:
        return redirect(url_for("doctor.dashboard"))

@auth_bp.route("/login", methods = ["GET", "POST"])     # route for user login, accepts GET and POST requests
def login():
    if request.method == "GET":     # if the request method is GET, render the login page
        return redirect(url_for("index"))     # redirect to the index page

    email = request.form.get("email", "").strip().lower()     # get the email from the form data
    password = request.form.get("password", "")     # get the password from the form data
    user = User.query.filter_by(email=email).first()     # query the database for the user with the given email

    if user is None or not user.check_password(password):     # check if the user exists and if the password is correct
        flash("Invalid email or password.")     # flash an error message if the email or password is invalid
        return redirect(url_for("index"))     # redirect to the index page

    login_user(user)     # log in the user if the email and password are valid
    # return redirect(url_for("patient.dashboard" if user.role == "patient" else "doctor.dashboard"))     # redirect to the appropriate dashboard based on the user's role
    
    # Redirect based on user role
    if user.role == "patient":
        return redirect(url_for("patient.dashboard"))
    elif user.role == "admin":
        return redirect(url_for("admin.dashboard"))
    else:
        return redirect(url_for("doctor.dashboard"))

@auth_bp.route("/logout")     # route for user logout
@login_required     # decorator to ensure that the user is logged in before accessing this route
def logout():
    logout_user()     # log out the user
    return redirect(url_for("index"))     # redirect to the index page
