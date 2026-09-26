from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from src.models import db, User, Doctor
from src.auth import role_required

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


