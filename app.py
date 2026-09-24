from flask import Flask, render_template        # import the Flask class and render_template function from the flask module  
from src.models import db       # import the database instance from the models module
from src.auth import auth_bp, init_auth       # import the authentication blueprint and initialization function from the auth module
from src.routes.patient import patient_bp       # import the patient blueprint from the patient module
from src.routes.doctor import doctor_bp     # import the doctor blueprint from the doctor module
from src.routes.admin import admin_bp       # import the admin blueprint from the  admin module

def create_app():        # define a function to create the Flask application
    app = Flask(__name__)        # create a new Flask application instance
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///medpilot.db'        # configure the database URI for SQLAlchemy
    app.config['SECRET_KEY'] = 'dev-secret-change-in-production'        # set a secret key for session management and security

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

    return app        # return the configured Flask application instance

app = create_app()        # create the Flask application instance by calling the create_app function

if __name__ == "__main__":        # check if the script is being run directly
    app.run(debug=True)        # run the Flask application in debug mode