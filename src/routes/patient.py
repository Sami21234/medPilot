from flask import Blueprint, render_template, request, redirect, url_for, flash     # used for routing and rendering templates
from flask_login import login_required, current_user        # used for user authentication and access control
from src.models import db, Case, Disease        # used for database operations and models
from src.auth import role_required        # used for role-based access control
from src import ml_service      # used for machine learning service integration

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')        # create a blueprint for patient routes

@patient_bp.route('/dashboard')        # define a route for the patient dashboard
@role_required('patient')        # restrict access to users with the 'patient' role
def dashboard():        # define the dashboard function
    cases = (Case.query.filter_by(patient_id=current_user.id)       # query the database for cases associated with the current user
                .order_by(Case.created_at.desc()).all())        # order the cases by creation date in descending order
    valid_symptoms = ml_service.get_valid_symptoms()        # get valid symptoms from the machine learning service
    return render_template('patient_dashboard.html', cases=cases, symptoms=valid_symptoms)        # render the dashboard template with the cases and valid symptoms

@patient_bp.route('/submit', methods=['POST'])        # define a route for submitting a new case
@role_required('patient')        # restrict access to users with the 'patient' role
def submit():        # define the submit_case function
    # Implementation for submitting a new case
    selected_symptoms = request.form.getlist('symptoms')        # get the selected symptoms from the form

    try:
        result = ml_service.predict_disease(selected_symptoms)        # call the machine learning service to predict the disease based on selected symptoms
    except ml_service.MLServiceError as e:        # handle any errors from the machine learning service
        flash(f"Error predicting disease: {str(e)}", 'danger')        # flash an error message to the user
        return redirect(url_for('patient.dashboard'))        # redirect back to the dashboard

    disease = Disease.query.filter_by(name=result['disease'])       # query the database for the predicted disease
    if disease is None:        # if the disease is not found in the database
        disease = Disease(name=result['disease'])        # create a new Disease object with the predicted disease name
        db.session.add(disease)        # add the new disease to the database session
        db.session.flush()        # flush the session to get the disease ID

    case = Case(
        patient_id=current_user.id,        # set the patient ID to the current user's ID
        symptoms_submitted=selected_symptoms,       # set the submitted symptoms to the selected symptoms
        predicted_disease_id=disease.id,        # set the disease ID to the predicted disease's ID
        confidence_score=result["confidence"],      # set the confidence score from the result
        status="pending_review",        # set the status of the case to "pending_review"
    )
    db.session.add(case)        # add the new case to the database session
    db.session.commit()        # commit the session to save the new case and disease to the

    flash("Your symptoms have been submitted and are awaiting doctor review.")
    return redirect(url_for("patient.dashboard"))

@patient_bp.route('/case/<int:case_id>')        # define a route for viewing a specific case
@role_required('patient')        # restrict access to users with the 'patient' role
def case_detail(case_id):        # define the case_detail function
    case = Case.query.get_or_404(case_id)        # query the database for the case with the given ID
    if case.patient_id != current_user.id:        # if the case does not belong to the current user
        from flask import abort        # import the abort function to handle unauthorized access
        abort(403)        # return a 403 Forbidden error

    return render_template('patient_case_detail.html', case=case)        # render the case detail template with the case information