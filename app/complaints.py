import logging
import os
import uuid
import warnings
from io import BytesIO

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from PIL import Image, UnidentifiedImageError
from sqlalchemy import false, or_
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename

from app import db
from app.auth import login_required
from app.models import Category, Complaint, Department
from app.services.data import create_complaint as create_complaint_record
from app.services.data import update_complaint as update_complaint_record

complaints_bp = Blueprint("complaints", __name__, url_prefix="/complaints")
ALLOWED_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
logger = logging.getLogger(__name__)


def _visible_query():
    query = Complaint.query
    if g.user.role in ("student", "staff"):
        query = query.filter_by(reporter_id=g.user.id)
    elif g.user.role == "officer":
        if g.user.department_id is None:
            query = query.filter(false())
        else:
            query = query.filter_by(department_id=g.user.department_id)
    return query


def _visible_complaint(complaint_id):
    complaint = _visible_query().filter_by(id=complaint_id).first()
    if complaint is None:
        abort(404)
    return complaint


def _save_upload(upload):
    if upload is None or not upload.filename:
        return None
    if len(upload.filename) > 255 or not secure_filename(upload.filename):
        raise ValueError("Choose a valid image filename.")
    data = upload.read(current_app.config["MAX_CONTENT_LENGTH"] + 1)
    if len(data) > current_app.config["MAX_CONTENT_LENGTH"]:
        raise ValueError("Images must be 5 MB or smaller.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(BytesIO(data))
            image.verify()
            image_format = image.format
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ValueError("Upload a valid JPEG, PNG, or WebP image.") from error
    extension = ALLOWED_IMAGE_FORMATS.get(image_format)
    if extension is None:
        raise ValueError("Upload a valid JPEG, PNG, or WebP image.")
    key = f"{uuid.uuid4().hex}{extension}"
    destination = os.path.join(current_app.config["UPLOAD_FOLDER"], key)
    with open(destination, "wb") as image_file:
        image_file.write(data)
    return key


def _delete_upload(image_key):
    if image_key:
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], image_key)
        if os.path.isfile(path):
            os.remove(path)


@complaints_bp.get("")
@login_required
def list_complaints():
    complaints = _visible_query().order_by(Complaint.created_at.desc()).all()
    return render_template("complaints/list.html", complaints=complaints)


@complaints_bp.route("/new", methods=["GET", "POST"])
@login_required
def create_complaint():
    if g.user.role not in ("student", "staff"):
        abort(403)
    categories = _active_categories()
    error = None
    if request.method == "POST":
        values = _complaint_values(categories)
        if isinstance(values, str):
            error = values
        else:
            category, title, description, location, priority = values
            image_key = None
            try:
                image_key = _save_upload(request.files.get("image"))
                complaint = create_complaint_record(
                    reporter=g.user,
                    category=category,
                    title=title,
                    description=description,
                    location=location,
                    priority=priority,
                    image_key=image_key,
                )
                db.session.commit()
            except ValueError as upload_error:
                db.session.rollback()
                _delete_upload(image_key)
                error = str(upload_error)
            except SQLAlchemyError:
                db.session.rollback()
                _delete_upload(image_key)
                logger.exception("Could not save a new complaint.")
                error = "The complaint could not be saved. Please try again."
            else:
                flash(f"Complaint {complaint.ticket_id} submitted.", "success")
                return redirect(
                    url_for("complaints.view_complaint", complaint_id=complaint.id)
                )
    if error:
        flash(error, "error")
    return render_template(
        "complaints/form.html", complaint=None, categories=categories
    )


@complaints_bp.get("/<int:complaint_id>")
@login_required
def view_complaint(complaint_id):
    complaint = _visible_complaint(complaint_id)
    return render_template("complaints/detail.html", complaint=complaint)


@complaints_bp.route("/<int:complaint_id>/edit", methods=["GET", "POST"])
@login_required
def edit_complaint(complaint_id):
    complaint = _visible_complaint(complaint_id)
    if complaint.status != "Submitted" or g.user.role not in ("student", "staff"):
        abort(403)
    categories = _active_categories()
    error = None
    if request.method == "POST":
        values = _complaint_values(categories)
        if isinstance(values, str):
            error = values
        else:
            category, title, description, location, priority = values
            new_image_key = None
            try:
                upload = request.files.get("image")
                if upload and upload.filename:
                    new_image_key = _save_upload(upload)
                old_image_key = complaint.image_key
                update_complaint_record(
                    complaint,
                    g.user,
                    {
                        "category": category,
                        "title": title,
                        "description": description,
                        "location": location,
                        "priority": priority,
                        "image_key": new_image_key or complaint.image_key,
                    },
                    "Complaint details updated.",
                )
                db.session.commit()
            except ValueError as upload_error:
                db.session.rollback()
                _delete_upload(new_image_key)
                error = str(upload_error)
            except SQLAlchemyError:
                db.session.rollback()
                _delete_upload(new_image_key)
                logger.exception("Could not update complaint %s.", complaint.id)
                error = "The complaint could not be updated. Please try again."
            else:
                if new_image_key:
                    _delete_upload(old_image_key)
                flash("Complaint updated.", "success")
                return redirect(
                    url_for("complaints.view_complaint", complaint_id=complaint.id)
                )
    if error:
        flash(error, "error")
    return render_template(
        "complaints/form.html", complaint=complaint, categories=categories
    )


@complaints_bp.get("/<int:complaint_id>/image")
@login_required
def complaint_image(complaint_id):
    complaint = _visible_complaint(complaint_id)
    if not complaint.image_key:
        abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        complaint.image_key,
        as_attachment=False,
        max_age=0,
    )


def _complaint_values(categories):
    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    priority = request.form.get("priority", "Normal")
    try:
        category_id = int(request.form.get("category_id", ""))
    except ValueError:
        return "Choose a valid category."
    category = next((item for item in categories if item.id == category_id), None)
    if category is None:
        return "Choose an active category."
    if not title or len(title) > 200:
        return "Titles must contain 1 to 200 characters."
    if not description or len(description) > 10000:
        return "Descriptions must contain 1 to 10,000 characters."
    if not location or len(location) > 200:
        return "Locations must contain 1 to 200 characters."
    if priority not in ("Low", "Normal", "High", "Urgent"):
        return "Choose a valid priority."
    return category, title, description, location, priority


def _active_categories():
    return (
        Category.query.outerjoin(Department, Category.default_department_id == Department.id)
        .filter(
            Category.is_active.is_(True),
            or_(
                Category.default_department_id.is_(None),
                Department.is_active.is_(True),
            ),
        )
        .order_by(Category.name)
        .all()
    )
