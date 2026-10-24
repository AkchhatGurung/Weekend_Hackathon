from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from app import db
from app.models import User
from app.extensions import login_manager

auth_bp = Blueprint("auth", __name__)


@auth_bp.before_app_request
def load_logged_in_user():
    g.user = current_user if current_user.is_authenticated else None
    if g.user is not None and not g.user.is_active:
        logout_user()
        g.user = None


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(**kwargs)

    return wrapped_view


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped_view(**kwargs):
            if g.user.role not in roles:
                return render_template(
                    "error.html", message="You are not authorized to access this page."
                ), 403
            return view(**kwargs)

        return wrapped_view

    return decorator


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("complaints.list_complaints"))

    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user is None or not user.is_active or not user.check_password(password):
            error = "Invalid email or password."
        else:
            login_user(user)
            return redirect(url_for("complaints.list_complaints"))

    if error:
        flash(error, "error")
    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have signed out.", "success")
    return redirect(url_for("auth.login"))
