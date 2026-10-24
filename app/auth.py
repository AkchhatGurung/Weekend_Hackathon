from functools import wraps
import re

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

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


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("complaints.list_complaints"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        password_confirmation = request.form.get("password_confirmation", "")

        if not name or len(name) > 120:
            flash("Enter your name (up to 120 characters).", "error")
        elif (
            len(email) > 255
            or re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email) is None
        ):
            flash("Enter a valid email address.", "error")
        elif len(password) < 12:
            flash("Your password must be at least 12 characters long.", "error")
        elif password != password_confirmation:
            flash("The password confirmation does not match.", "error")
        elif User.query.filter_by(email=email).first() is not None:
            flash("An account with that email already exists. Please sign in.", "error")
        else:
            user = User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role="student",
            )
            db.session.add(user)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("An account with that email already exists. Please sign in.", "error")
            else:
                login_user(user)
                flash("Your student account is ready. Welcome to Smart Campus!", "success")
                return redirect(url_for("complaints.list_complaints"))

    return render_template("auth/register.html")


@auth_bp.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have signed out.", "success")
    return redirect(url_for("auth.login"))
