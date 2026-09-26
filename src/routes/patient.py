# from flask import Blueprint, render_template, request, redirect, url_for, flash     # used for routing and rendering templates
# from flask_login import login_required, current_user        # used for user authentication and access control
# from src.models import db, Case, Disease        # used for database operations and models
# from src.auth import role_required        # used for role-based access control
# from src.ml_service import predict      # used for machine learning service integration

# patient_bp = Blueprint('patient', __name__, url_prefix='/patient')        # create a blueprint for patient routes

# @patient_bp.route('/dashboard', methods = ["GET"])        # define a route for the patient dashboard
# @login_required
# @role_required('patient')        # restrict access to users with the 'patient' role
# def dashboard():        # define the dashboard function
#     cases = (Case.query.filter_by(patient_id=current_user.id)       # query the database for cases associated with the current user
#                 .order_by(Case.created_at.desc()).all())        # order the cases by creation date in descending order
#     valid_symptoms = ml_service.get_valid_symptoms()        # get valid symptoms from the machine learning service
#     return render_template('patient_dashboard.html', cases=cases, symptoms=valid_symptoms)        # render the dashboard template with the cases and valid symptoms

# @patient_bp.route('/submit', methods=['POST'])        # define a route for submitting a new case
# @role_required('patient')        # restrict access to users with the 'patient' role
# def submit():        # define the submit_case function
#     # Implementation for submitting a new case
#     selected_symptoms = request.form.getlist('symptoms')        # get the selected symptoms from the form

#     try:
#         result = ml_service.predict(selected_symptoms)        # call the machine learning service to predict the disease based on selected symptoms
#     except ml_service.InvalidSymptomError as e:        # handle any errors from the machine learning service
#         flash(f"Error predicting disease: {str(e)}", 'danger')        # flash an error message to the user
#         return redirect(url_for('patient.dashboard'))        # redirect back to the dashboard

#     disease = Disease.query.filter_by(name=result['disease']).first()       # query the database for the predicted disease
#     if disease is None:        # if the disease is not found in the database
#         disease = Disease(name=result['disease'])        # create a new Disease object with the predicted disease name
#         db.session.add(disease)        # add the new disease to the database session
#         db.session.flush()        # flush the session to get the disease ID

#     case = Case(
#         patient_id=current_user.id,        # set the patient ID to the current user's ID
#         symptoms_submitted=selected_symptoms,       # set the submitted symptoms to the selected symptoms
#         predicted_disease_id=disease.id,        # set the disease ID to the predicted disease's ID
#         confidence_score=result["confidence"],      # set the confidence score from the result
#         status="pending_review",        # set the status of the case to "pending_review"
#     )
#     db.session.add(case)        # add the new case to the database session
#     db.session.commit()        # commit the session to save the new case and disease to the

#     flash("Your symptoms have been submitted and are awaiting doctor review.")
#     return redirect(url_for("patient.dashboard"))

# @patient_bp.route('/case/<int:case_id>')        # define a route for viewing a specific case
# @role_required('patient')        # restrict access to users with the 'patient' role
# def case_detail(case_id):        # define the case_detail function
#     case = Case.query.get_or_404(case_id)        # query the database for the case with the given ID
#     if case.patient_id != current_user.id:        # if the case does not belong to the current user
#         from flask import abort        # import the abort function to handle unauthorized access
#         abort(403)        # return a 403 Forbidden error

#     return render_template('patient_case_detail.html', case=case)        # render the case detail template with the case information

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.auth import role_required
from src.models import db, Case, Disease
from src.ml_service import predict, get_valid_symptoms, InvalidSymptomError

patient_bp = Blueprint('patient', __name__, url_prefix='/patient')

@patient_bp.route('/dashboard', methods=['GET'])
@login_required
@role_required('patient')
def dashboard():
    # Fetch all submission records for current logged-in patient
    cases = Case.query.filter_by(patient_id=current_user.id).order_by(Case.created_at.desc()).all()

    symptoms = get_valid_symptoms()  # Get valid symptoms from the ML service
    return render_template('patient_dashboard.html', symptoms=symptoms, cases=cases)

@patient_bp.route('/submit', methods=['POST'])
@login_required
@role_required('patient')
def submit_symptoms():
    # Extract selected symptom checkbox strings from submitted form
    selected_symptoms = request.form.getlist('symptoms')
    
    try:
        # Run inference through ml_service
        prediction = predict(selected_symptoms)
    except InvalidSymptomError as e:
        flash(str(e), 'danger')
        return redirect(url_for('patient.dashboard'))
    except Exception as e:
        flash(f"Prediction failure: {e}", 'danger')
        return redirect(url_for('patient.dashboard'))
    
    # Look up corresponding Disease record ID from database
    predicted_disease = Disease.query.filter_by(name=prediction['disease']).first()
    predicted_disease_id = predicted_disease.id if predicted_disease else None
    
    # Create Case row initialized to pending_review state
    new_case = Case(
        patient_id=current_user.id,
        symptoms_submitted=selected_symptoms,
        predicted_disease_id=predicted_disease_id,
        confidence_score=prediction['confidence'],
        status='pending_review'
    )
    
    db.session.add(new_case)
    db.session.commit()
    
    flash('Symptoms submitted successfully. Your case is pending doctor review.', 'success')
    return redirect(url_for('patient.dashboard'))

@patient_bp.route('/cases/<int:case_id>', methods=['GET'])
@login_required
@role_required('patient')
def view_case(case_id):
    case = Case.query.get_or_404(case_id)
    
    # Restrict viewing access so patients can only access their own cases
    if case.patient_id != current_user.id:
        flash('Unauthorized access to this case.', 'danger')
        return redirect(url_for('patient.dashboard'))
        
    return render_template('patient_case_detail.html', case=case)