from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from src.models import db, User, Doctor
from src.auth import role_required
from src.models import Case

admin_bp = Blueprint("admin", __name__, url_prefix = "/admin")  

@admin_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("admin")
def dashboard():
    unverified_doctors = Doctor.query.filter_by(is_verified=False).all()
    verified_doctors = Doctor.query.filter_by(is_verified=True).all()
    return render_template(
        "admin_dashboard.html",
        unverified_doctors=unverified_doctors,
        verified_doctors=verified_doctors
    )

@admin_bp.route("/verify/<int:doctor_user_id>", methods=["POST"])
@login_required
@role_required("admin")
def verify(doctor_user_id):
    doctor = Doctor.query.filter_by(user_id=doctor_user_id).first_or_404()
    doctor.is_verified = True
    db.session.commit()
    flash(f"Dr. {doctor.user.name} verified successfully.")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/analytics")
@login_required
@role_required("admin")
def analytics():
    validated_cases = Case.query.filter_by(status = "validated").all()
    total = len(validated_cases)
    agreed = sum(1 for c in validated_cases if c.predicted_disease_id == c.final_disease_id)
    overridden = total - agreed
    agreement_rate = round((agreed / total * 100), 1) if total else 0

    # Per-disease breakdown -- which diseases get overridden most often
    from collections import defaultdict
    per_disease = defaultdict(lambda: {"agreed": 0, "overridden": 0})
    for c in validated_cases:
        key = c.predicted_disease.name if c.predicted_disease else "Unknown"
        if c.predicted_disease_id == c.final_disease_id:
            per_disease[key]["agreed"] += 1
        else:
            per_disease[key]["overridden"] += 1

    return render_template(
        "admin_analytics.html",
        total=total, agreed=agreed, overridden=overridden,
        agreement_rate=agreement_rate, per_disease=dict(per_disease)
    )


