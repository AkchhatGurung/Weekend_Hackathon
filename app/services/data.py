from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app import db
from app.constants import MIN_PASSWORD_LENGTH
from app.models import (
    Category,
    Complaint,
    ComplaintHistory,
    Department,
    Feedback,
    User,
)

VALID_ROLES = {"student", "staff", "officer", "admin"}
VALID_PRIORITIES = {"Low", "Normal", "High", "Urgent"}
VALID_STATUSES = {"Submitted", "In Progress", "Resolved", "Rejected", "Cancelled"}


def utcnow():
    return datetime.now(timezone.utc)


def _require(value, field):
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"{field} is required.")
    return value.strip() if isinstance(value, str) else value


def _validate_complaint_text(value, field, maximum):
    value = _require(value, field)
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f"{field} must contain 1 to {maximum} characters.")
    return value


def create_department(name):
    department = Department(name=_require(name, "Department name"))
    db.session.add(department)
    db.session.flush()
    return department


def update_department(department, name):
    department.name = _require(name, "Department name")
    db.session.flush()
    return department


def create_category(name, default_department=None):
    category = Category(
        name=_require(name, "Category name"),
        default_department=default_department,
    )
    db.session.add(category)
    db.session.flush()
    return category


def update_category(category, name, default_department=None):
    category.name = _require(name, "Category name")
    category.default_department = default_department
    db.session.flush()
    return category


def create_user(name, email, password, role, department=None):
    normalized_email = _require(email, "Email").lower()
    if role not in VALID_ROLES:
        raise ValueError("Invalid user role.")
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(
            f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    user = User(
        name=_require(name, "Name"),
        email=normalized_email,
        password_hash=generate_password_hash(password),
        role=role,
        department=department,
    )
    db.session.add(user)
    db.session.flush()
    return user


def update_user(user, name, email, role, department=None, password=None):
    if role not in VALID_ROLES:
        raise ValueError("Invalid user role.")
    user.name = _require(name, "Name")
    user.email = _require(email, "Email").lower()
    user.role = role
    user.department = department
    if password:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters long."
            )
        user.password_hash = generate_password_hash(password)
    db.session.flush()
    return user


def create_complaint(
    reporter,
    category,
    title,
    description,
    location,
    priority="Normal",
    image_key=None,
    remarks="Complaint submitted.",
):
    if priority not in VALID_PRIORITIES:
        raise ValueError("Invalid complaint priority.")
    if not reporter or not reporter.is_active:
        raise ValueError("An active reporter is required.")
    if not category or not category.is_active:
        raise ValueError("An active category is required.")

    complaint = Complaint(
        reporter=reporter,
        category=category,
        department=category.default_department,
        title=_validate_complaint_text(title, "Title", 200),
        description=_validate_complaint_text(description, "Description", 10000),
        location=_validate_complaint_text(location, "Location", 200),
        priority=priority,
        image_key=image_key,
    )
    db.session.add(complaint)
    db.session.flush()
    # The database-generated primary-key sequence is concurrency-safe.
    complaint.ticket_id = f"SCG-{complaint.id:08d}"
    db.session.add(
        ComplaintHistory(
            complaint=complaint,
            actor_id=reporter.id,
            action="Submitted",
            new_status=complaint.status,
            remarks=remarks,
        )
    )
    db.session.flush()
    return complaint


def update_complaint(complaint, actor, values, remarks):
    if actor.id != complaint.reporter_id and actor.role not in {"officer", "admin"}:
        raise ValueError("You are not allowed to update this complaint.")
    if complaint.status != "Submitted":
        raise ValueError("Only submitted complaints can be edited.")
    category = values.get("category", complaint.category)
    if not category or not category.is_active:
        raise ValueError("An active category is required.")
    priority = values.get("priority", complaint.priority)
    if priority not in VALID_PRIORITIES:
        raise ValueError("Invalid complaint priority.")
    old_status = complaint.status
    complaint.category = category
    complaint.department = category.default_department
    for field in ("title", "description", "location", "image_key"):
        if field in values:
            if field != "image_key":
                maximum = {"title": 200, "description": 10000, "location": 200}[field]
                values[field] = _validate_complaint_text(values[field], field.title(), maximum)
            setattr(complaint, field, values[field])
    complaint.priority = priority
    db.session.add(
        ComplaintHistory(
            complaint=complaint,
            actor_id=actor.id,
            action="Edited",
            old_status=old_status,
            new_status=complaint.status,
            remarks=remarks,
        )
    )
    db.session.flush()
    return complaint


def get_complaint(complaint_id):
    return db.session.get(Complaint, complaint_id)


def get_complaint_by_ticket(ticket_id):
    ticket_id = _require(ticket_id, "Ticket ID")
    return db.session.scalar(select(Complaint).where(Complaint.ticket_id == ticket_id))


def can_access_complaint(actor, complaint):
    if actor is None or complaint is None:
        return False
    if actor.role == "admin":
        return True
    if actor.role == "officer":
        return actor.department_id is not None and actor.department_id == complaint.department_id
    return actor.id == complaint.reporter_id


def cancel_complaint(complaint, actor, remarks="Complaint cancelled by reporter."):
    if not can_access_complaint(actor, complaint) or actor.role not in {"student", "staff"}:
        raise ValueError("You are not allowed to cancel this complaint.")
    if complaint.status != "Submitted":
        raise ValueError("Only submitted complaints can be cancelled.")
    complaint.status = "Cancelled"
    db.session.add(
        ComplaintHistory(
            complaint=complaint,
            actor_id=actor.id,
            action="Cancelled",
            old_status="Submitted",
            new_status="Cancelled",
            remarks=_require(remarks, "Remarks"),
        )
    )
    db.session.flush()
    return complaint


def list_complaints(
    *, reporter_id=None, department_id=None, status=None, category_id=None,
    date_from=None, date_to=None, page=None, per_page=20
):
    statement = select(Complaint).order_by(Complaint.created_at.desc())
    if reporter_id is not None:
        statement = statement.where(Complaint.reporter_id == reporter_id)
    if department_id is not None:
        statement = statement.where(Complaint.department_id == department_id)
    if status is not None:
        if status not in VALID_STATUSES:
            raise ValueError("Invalid complaint status.")
        statement = statement.where(Complaint.status == status)
    if category_id is not None:
        statement = statement.where(Complaint.category_id == category_id)
    if date_from is not None:
        statement = statement.where(Complaint.created_at >= _date_boundary(date_from, False))
    if date_to is not None:
        statement = statement.where(Complaint.created_at < _date_boundary(date_to, True))
    if page is not None:
        if page < 1 or per_page < 1 or per_page > 100:
            raise ValueError("Page must be positive and per_page must be between 1 and 100.")
        return db.paginate(statement, page=page, per_page=per_page, error_out=False)
    return db.session.scalars(statement).all()


def _date_boundary(value, end):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        if end:
            return datetime.combine(value, time.min, tzinfo=timezone.utc) + timedelta(days=1)
        return datetime.combine(value, time.min, tzinfo=timezone.utc)
    try:
        parsed = date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError("Dates must use YYYY-MM-DD format.") from error
    if end:
        return datetime.combine(parsed, time.min, tzinfo=timezone.utc) + timedelta(days=1)
    return datetime.combine(parsed, time.min, tzinfo=timezone.utc)


def add_feedback(complaint, rating, comments=None):
    if not 1 <= rating <= 5:
        raise ValueError("Feedback rating must be between 1 and 5.")
    feedback = Feedback(complaint=complaint, rating=rating, comments=comments)
    db.session.add(feedback)
    db.session.flush()
    return feedback


def deactivate_record(record):
    if not hasattr(record, "is_active"):
        raise ValueError("This record does not support deactivation.")
    record.is_active = False
    db.session.flush()
    return record


def commit():
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise
