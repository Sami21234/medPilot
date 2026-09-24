from datetime import datetime           
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort      
from flask_login import current_user
from src.models import db, Case, Disease, Doctor      
from src.auth import role_required

doctor_bp = Blueprint("doctor", __name__, url_prefix= "/doctor")

def _verified_doctor_required():        
    profile = Doctor.query.get(current_user.id)
    return profile is not None and profile.is_verified

@doctor_bp.route("/dashboard")
@role_required("doctor")
def dashboard():
    if not _verified_doctor_required():
        return render_template("doctor_pending_verification.html")
    pending_cases = (Case.query.filter_by(status = "pending_review")
                     .order_by(Case.created_at.asc()).all())
    return render_template("doctor_dashboard.html", cases = pending_cases)

@doctor_bp.route("/cases/<int:case_id>")
@role_required("doctor")
def case_detail(case_id):
    if not _verified_doctor_required():
        return render_template("doctor_pending_verification.html")
    case = Case.query.get_or_404(case_id)
    all_diseases = Disease.query.order_by(Disease.name).all()
    return render_template("doctor_case_detail.html", case = case, all_diseases = all_diseases)

@doctor_bp.route("/cases/<int:case_id>/validate", methods = ["POST"])
@role_required("doctor")
def validate(case_id):
    if not _verified_doctor_required():
        abort(403)
    case = Case.query.get_or_404(case_id)
    if case.status != "pending_review":
        flash("This case has already been reviewed.")
        return redirect(url_for("doctor.dashboard"))

    decision = request.form.get("decision")
    notes = request.form.get("notes", "")

    if decision == "confirm":
        case.final_disease_id = case.predicted_disease_id
    elif decision == "override":
        override_disease_id = request.form.get("override_disease_id")
        if not override_disease_id:
            flash("Select a disease to override with.")
            return redirect(url_for("doctor.case_detail", case_id=case_id))
        case.final_disease_id = int(override_disease_id)
    else:
        flash("Invalid decision.")
        return redirect(url_for("doctor.case_detail", case_id=case_id))

    case.status = "validated"
    case.doctor_id = current_user.id
    case.doctor_notes = notes
    case.validated_at = datetime.utcnow()
    db.session.commit()
    flash(f"Case #{case.id} validated.")
    return redirect(url_for("doctor.dashboard"))

