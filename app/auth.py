from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


@auth_bp.before_app_request
def load_logged_in_user():
    user_id = session.get("user_id")
    g.user = db.session.get(User, user_id) if user_id is not None else None
    if g.user is not None and not g.user.is_active:
        session.clear()
        g.user = None


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
            session.clear()
            session["user_id"] = user.id
            return redirect(url_for("complaints.list_complaints"))

    if error:
        flash(error, "error")
    return render_template("auth/login.html")


@auth_bp.post("/logout")
@login_required
def logout():
    session.clear()
    flash("You have signed out.", "success")
    return redirect(url_for("auth.login"))
