from flask import Blueprint, render_template, redirect, url_for, flash
from src.models import db, User, Doctor
from src.auth import role_required

admin_bp = Blueprint("admin", __name__, url_prefix = "/admin")  

@admin_bp.route("/verify/<int:doctor_user_id>", methods=["POST"])
@role_required("admin")
def verify(doctor_user_id):
    doctor = Doctor.query.get_or_404(doctor_user_id)
    doctor.is_verified = True
    db.session.commit()
    flash(f"Dr. {doctor.user.name} verified.")
    return redirect(url_for("admin.dashboard"))


