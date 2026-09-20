# This file defines the database models for the application, including the User model for user authentication and management.

from datetime import datetime       # for timestamping user creation
from flask_sqlalchemy import SQLAlchemy     # create a SQLAlchemy instance for database management
from flask_login import UserMixin       # for user session management and authentication
from werkzeug.security import generate_password_hash, check_password_hash       # for password hashing and verification

db = SQLAlchemy()     # create a SQLAlchemy instance for database management

class User(UserMixin, db.Model):     # define the User model, inheriting from UserMixin and db.Model
    """Base account. role determines which portal a user can access."""

    __tablename__ = 'users'     # specify the table name for the User model

    id = db.Column(db.Integer, primary_key=True)     # define the primary key column for the User model
    name = db.Column(db.String(120), nullable=False)     # define the name column for the User model
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)     # define the email column for the User model
    password_hash = db.Column(db.String(255), nullable=False)     # define the password hash column for the User model
    role = db.Column(db.String(20), nullable=False)     # define the role column for the User model
    created_at = db.Column(db.DateTime, default=datetime.utcnow)     # define the created_at column for the User model

    # set_password and check_password methods are used for password management, ensuring that passwords are stored securely as hashes and can be verified during login.
    def set_password(self, password):     # method to set the password for a user
        self.password_hash = generate_password_hash(password)     # hash and store the password

    def check_password(self, password):     # method to check if a given password matches the stored password hash
        return check_password_hash(self.password_hash, password)     # verify the password against the stored hash

class Doctor(db.Model):     # define the Doctor model, inheriting from db.Model
    """Extra fields for doctor accounts. is_verified gates doctor-portal access."""

    __tablename__ = 'doctors'     # specify the table name for the Doctor model

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)     # define the primary key column for the Doctor model
    specialization = db.Column(db.String(120))     # define the specialization column for the Doctor model
    license_number = db.Column(db.String(60))     # define the license number column for the Doctor model
    is_verified = db.Column(db.Boolean, default=False)     # define the is_verified column for the Doctor model

    user = db.relationship('User', backref='doctor_profile')     # define the relationship between the Doctor and User models(backref allows access to the doctor profile from the user instance)

class Patient(db.Model):     # define the Patient model, inheriting from db.Model
    """Extra fields for patient accounts."""

    __tablename__ = 'patients'     # specify the table name for the Patient model

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)     # define the primary key column for the Patient model
    age = db.Column(db.Integer)     # define the age column for the Patient model
    gender = db.Column(db.String(20))     # define the gender column for the Patient model

    user = db.relationship('User', backref='patient_profile')     # define the relationship between the Patient and User models(backref allows access to the patient profile from the user instance)

class Disease(db.Model):     # define the Disease model, inheriting from db.Model
    """Disease information."""

    __tablename__ = 'diseases'     # specify the table name for the Disease model

    id = db.Column(db.Integer, primary_key=True)     # define the primary key column for the Disease model
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)     # define the name column for the Disease model
    description = db.Column(db.Text)     # define the description column for the Disease model

class Medication(db.Model):     # define the Medication model, inheriting from db.Model
    """Medication information."""

    __tablename__ = 'medications'     # specify the table name for the Medication model

    id = db.Column(db.Integer, primary_key=True)     # define the primary key column for the Medication model
    disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=False)     # define the foreign key column for the Medication model, linking to the Disease model
    content = db.Column(db.Text, nullable=False)     # define the content column for the Medication model
    disease = db.relationship('Disease', backref='medications')     # define the relationship between the Medication and Disease models(backref allows access to the medications from the disease instance)

class Precaution(db.Model):     # define the Precaution model, inheriting from db.Model
    """Precaution information."""

    __tablename__ = 'precautions'     # specify the table name for the Precaution model

    id = db.Column(db.Integer, primary_key=True)     # define the primary key column for the Precaution model
    disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=False)     # define the foreign key column for the Precaution model, linking to the Disease model
    content = db.Column(db.Text, nullable=False)     # define the content column for the Precaution model
    disease = db.relationship('Disease', backref='precautions')     # define the relationship between the Precaution and Disease models(backref allows access to the precautions from the disease instance)

class Workout(db.Model):     # define the Workout model, inheriting from db.Model
    """Workout information."""

    __tablename__ = 'workouts'     # specify the table name for the Workout model

    id = db.Column(db.Integer, primary_key=True)     # define the primary key column for the Workout model
    disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=False)     # define the foreign key column for the Workout model, linking to the Disease model
    content = db.Column(db.Text, nullable=False)     # define the content column for the Workout model
    disease = db.relationship('Disease', backref='workouts')     # define the relationship between the Workout and Disease models(backref allows access to the workouts from the disease instance)

class Symptom(db.Model):     # define the Symptom model, inheriting from db.Model
    """Symptom information."""

    __tablename__ = 'symptoms'     # specify the table name for the Symptom model

    id = db.Column(db.Integer, primary_key=True)     # define the primary key column for the Symptom model
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)     # define the name column for the Symptom model
    severity_weight = db.Column(db.Float, default=0.0)     # define the severity weight column for the Symptom model, which can be used to indicate the severity of the symptom

class Case(db.Model):     # define the Case model, inheriting from db.Model
    """
    A single patient submission -> AI prediction -> doctor validation cycle.
    predicted_disease_id and final_disease_id are kept SEPARATE and never
    overwritten -- this is the audit trail (see architecture.md Section 3.1).
    """

    __tablename__ = 'cases'     # specify the table name for the Case model

    id = db.Column(db.Integer, primary_key=True)     # define the primary key column for the Case model
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)     # define the foreign key column for the Case model, linking to the Patient model

    symptoms_submitted = db.Column(db.JSON, nullable=False)     # list of symptom names
    predicted_disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'))     # define the foreign key column for the Case model, linking to the Disease model
    confidence_score = db.Column(db.Float)     # define the confidence score column for the Case model, which can be used to indicate the confidence of the AI prediction

    status = db.Column(db.String(20), default="pending_review")     # define the status column for the Case model, which can be used to indicate the current status of the case (e.g., pending_review | validated | rejected)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)     # define the foreign key column for the Case model, linking to the Doctor model
    final_disease_id = db.Column(db.Integer, db.ForeignKey('diseases.id'), nullable=True)     # define the foreign key column for the Case model, linking to the Disease model

    created_at = db.Column(db.DateTime, default=datetime.utcnow)     # define the created_at column for the Case model
    validated_at = db.Column(db.DateTime, nullable=True)     # define the validated_at column for the Case model, which can be used to indicate when the case was validated by a doctor

    patient = db.relationship('User', foreign_keys=[patient_id], backref='submitted_cases')     # define the relationship between the Case and Patient models(backref allows access to the cases from the patient instance)
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref='validated_cases')     # define the relationship between the Case and Doctor models(backref allows access to the cases from the doctor instance)
    predicted_disease = db.relationship('Disease', foreign_keys=[predicted_disease_id])     # define the relationship between the Case and Disease models for the predicted disease
    final_disease = db.relationship('Disease', foreign_keys=[final_disease_id])     # define the relationship between the Case and Disease models for the final disease
