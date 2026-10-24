import re

from flask import Blueprint, flash, redirect, render_template, request, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import db
from app.auth import roles_required
from app.models import Category, Department, User

management_bp = Blueprint("management", __name__, url_prefix="/admin")
VALID_ROLES = ("student", "staff", "officer", "admin")
EMAIL_PATTERN = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@management_bp.get("/")
@roles_required("admin")
def index():
    return render_template(
        "admin/index.html",
        departments=Department.query.order_by(Department.name).all(),
        categories=Category.query.order_by(Category.name).all(),
        users=User.query.order_by(User.name).all(),
    )


@management_bp.post("/departments")
@roles_required("admin")
def create_department():
    name = request.form.get("name", "").strip()
    if not name or len(name) > 100:
        flash("Department names must contain 1 to 100 characters.", "error")
    else:
        db.session.add(Department(name=name))
        return _commit("Department created.")
    return redirect(url_for("management.index"))


@management_bp.post("/departments/<int:department_id>")
@roles_required("admin")
def update_department(department_id):
    department = db.get_or_404(Department, department_id)
    name = request.form.get("name", "").strip()
    if not name or len(name) > 100:
        flash("Department names must contain 1 to 100 characters.", "error")
    else:
        department.name = name
        department.is_active = request.form.get("is_active") == "on"
        return _commit("Department updated.")
    return redirect(url_for("management.index"))


@management_bp.post("/categories")
@roles_required("admin")
def create_category():
    name = request.form.get("name", "").strip()
    department = _selected_department(request.form.get("department_id"))
    if not name or len(name) > 80:
        flash("Category names must contain 1 to 80 characters.", "error")
    elif department is False:
        flash("Choose an existing department or leave it unassigned.", "error")
    else:
        db.session.add(
            Category(
                name=name,
                default_department=department,
            )
        )
        return _commit("Category created.")
    return redirect(url_for("management.index"))


@management_bp.post("/categories/<int:category_id>")
@roles_required("admin")
def update_category(category_id):
    category = db.get_or_404(Category, category_id)
    name = request.form.get("name", "").strip()
    department = _selected_department(request.form.get("department_id"))
    if not name or len(name) > 80:
        flash("Category names must contain 1 to 80 characters.", "error")
    elif department is False:
        flash("Choose an existing department or leave it unassigned.", "error")
    else:
        category.name = name
        category.default_department = department
        category.is_active = request.form.get("is_active") == "on"
        return _commit("Category updated.")
    return redirect(url_for("management.index"))


@management_bp.post("/users")
@roles_required("admin")
def create_user():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    role = request.form.get("role", "")
    department = _selected_department(request.form.get("department_id"))
    if not name or len(name) > 120 or not _valid_email(email):
        flash("Enter a valid name and email address.", "error")
    elif len(password) < 12:
        flash("Passwords must be at least 12 characters long.", "error")
    elif role not in VALID_ROLES:
        flash("Choose a valid role.", "error")
    elif department is False:
        flash("Choose an existing department or leave it unassigned.", "error")
    else:
        db.session.add(
            User(
                name=name,
                email=email,
                password_hash=generate_password_hash(password),
                role=role,
                department=department,
            )
        )
        return _commit("User created.")
    return redirect(url_for("management.index"))


@management_bp.post("/users/<int:user_id>")
@roles_required("admin")
def update_user(user_id):
    user = db.get_or_404(User, user_id)
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    role = request.form.get("role", "")
    department = _selected_department(request.form.get("department_id"))
    password = request.form.get("password", "")
    if not name or len(name) > 120 or not _valid_email(email):
        flash("Enter a valid name and email address.", "error")
    elif role not in VALID_ROLES:
        flash("Choose a valid role.", "error")
    elif department is False:
        flash("Choose an existing department or leave it unassigned.", "error")
    elif password and len(password) < 12:
        flash("Passwords must be at least 12 characters long.", "error")
    else:
        user.name = name
        user.email = email
        user.role = role
        user.department = department
        user.is_active = request.form.get("is_active") == "on"
        if password:
            user.password_hash = generate_password_hash(password)
        return _commit("User updated.")
    return redirect(url_for("management.index"))


def _selected_department(raw_id):
    if not raw_id:
        return None
    try:
        department_id = int(raw_id)
    except ValueError:
        return False
    department = db.session.get(Department, department_id)
    return department if department and department.is_active else False


def _valid_email(email):
    return len(email) <= 255 and EMAIL_PATTERN.fullmatch(email) is not None


def _commit(success_message):
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("A record with that name or email already exists.", "error")
    else:
        flash(success_message, "success")
    return redirect(url_for("management.index"))
