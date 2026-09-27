import os
from flask import Flask, render_template        # import the Flask class and render_template function from the flask module  
from src.models import db, User, Disease       # import the database instances from the models module
from src.auth import auth_bp, init_auth       # import the authentication blueprint and initialization function from the auth module
from src.routes.patient import patient_bp       # import the patient blueprint from the patient module
from src.routes.doctor import doctor_bp     # import the doctor blueprint from the doctor module
from src.routes.admin import admin_bp       # import the admin blueprint from the  admin module

def seed_disease_if_empty():
    """Runs the same logic as seed_diseases.py, but only if the table is empty.
    Safe to call on every startup -- never duplicates data."""
    if Disease.query.first() is not None:
        return  # already seeded, nothing to do

    import ast
    import pandas as pd
    from src.models import Medication, Diet, Precaution, Workout

    desc = pd.read_csv("data/processed/description_clean.csv")
    meds = pd.read_csv("data/processed/medications_clean.csv")
    diets = pd.read_csv("data/processed/diets_clean.csv")
    precau = pd.read_csv("data/processed/precautions_clean.csv")
    workout = pd.read_csv("data/processed/workout_clean.csv")

    def get_or_create_disease(name, description = None):
        d = Disease.query.filter_by(name = name).first()
        if d is None:
            d = Disease(name = name, description = description)
            db.session.add(d)
            db.session.flush()
        elif description and not d.description:
            d.description = description
        return d

    for _, row in desc.iterrows():
        get_or_create_disease(row["Disease"], row["Description"])

    def parse_list_field(value):
        if pd.isna(value):
            return []
        try:
            parsed = ast.literal_eval(value)
            return parsed if isinstance(parsed, list) else [str(parsed)]
        except (ValueError, SyntaxError):
            return [str(value)]

    for _, row in meds.iterrows():
        d = get_or_create_disease(row["Disease"])
        for item in parse_list_field(row["Medication"]):
            db.session.add(Medication(disease_id=d.id, content=item))

    for _, row in diets.iterrows():
        d = get_or_create_disease(row["Disease"])
        for item in parse_list_field(row["Diet"]):
            db.session.add(Diet(disease_id=d.id, content=item))

    precaution_cols = [c for c in precau.columns if c.lower().startswith("precaution")]
    for _, row in precau.iterrows():
        d = get_or_create_disease(row["Disease"])
        for col in precaution_cols:
            if pd.notna(row[col]) and str(row[col]).strip():
                db.session.add(Precaution(disease_id=d.id, content=row[col]))

    for _, row in workout.iterrows():
        d = get_or_create_disease(row["disease"])
        db.session.add(Workout(disease_id=d.id, content=row["workout"]))

    db.session.commit()
    print(f"[seed] Seeded {Disease.query.count()} diseases.")

def seed_admin_if_missing():
    """Creates an admin from environment variables, only if no admin exists yet.
    No input() needed -- reads ADMIN_EMAIL/ADMIN_NAME/ADMIN_PASSWORD from
    Render's Environment Variables tab instead."""
    if User.query.filter_by(role="admin").first() is not None:
        return  # admin already exists

    email = os.environ.get("ADMIN_EMAIL")
    name = os.environ.get("ADMIN_NAME")
    password = os.environ.get("ADMIN_PASSWORD")

    if not (email and name and password):
        print("[seed] No ADMIN_EMAIL/ADMIN_NAME/ADMIN_PASSWORD set -- skipping admin creation.")
        return

    admin = User(name=name, email=email.strip().lower(), role="admin")
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()
    print(f"[seed] Admin account created: {email}")

def create_app():        # define a function to create the Flask application
    app = Flask(__name__)        # create a new Flask application instance
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medpilot.db'        # configure the database URI for SQLAlchemy
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY","dev-secret-change-in-production")        # set a secret key for session management and security

    db.init_app(app)        # initialize the database with the Flask application
    init_auth(app)        # initialize authentication with the Flask application

    app.register_blueprint(auth_bp)        # register the authentication blueprint with the Flask application
    app.register_blueprint(patient_bp)        # register the patient blueprint with the Flask application
    app.register_blueprint(doctor_bp)       # register the doctor blueprint with the Flask application
    app.register_blueprint(admin_bp)        # register the admin blueprint with the Flask application

    @app.route("/")        # define a route for the home page
    def index():        # define the index function to handle requests to the home page
        return render_template("index.html")        # render the index.html template for the home page

    with app.app_context():        # create an application context for the Flask application
        db.create_all()        # create all database tables defined in the models
        seed_disease_if_empty()
        seed_admin_if_missing()

    return app        # return the configured Flask application instance

app = create_app()        # create the Flask application instance by calling the create_app function

if __name__ == "__main__":        # check if the script is being run directly
    app.run(debug=True)        # run the Flask application in debug mode