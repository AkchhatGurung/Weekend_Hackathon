from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash

from app import db

ID_TYPE = db.BigInteger().with_variant(db.Integer, "sqlite")


def utcnow():
    return datetime.now(timezone.utc)


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(ID_TYPE, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    is_active = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.true()
    )

    categories = db.relationship(
        "Category", back_populates="default_department", passive_deletes=True
    )
    complaints = db.relationship(
        "Complaint", back_populates="department", passive_deletes=True
    )


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(ID_TYPE, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    department_id = db.Column(
        ID_TYPE, db.ForeignKey("departments.id"), nullable=True
    )
    is_active = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.true()
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=db.func.now(),
    )

    department = db.relationship("Department", passive_deletes=True)
    complaints = db.relationship(
        "Complaint",
        foreign_keys="Complaint.reporter_id",
        back_populates="reporter",
        passive_deletes=True,
    )

    __table_args__ = (
        db.CheckConstraint(
            "role IN ('student', 'staff', 'officer', 'admin')", name="ck_users_role"
        ),
    )

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Category(db.Model):
    __tablename__ = "categories"

    id = db.Column(ID_TYPE, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    default_department_id = db.Column(
        ID_TYPE, db.ForeignKey("departments.id"), nullable=True
    )
    is_active = db.Column(
        db.Boolean, nullable=False, default=True, server_default=db.true()
    )

    default_department = db.relationship(
        "Department", back_populates="categories"
    )
    complaints = db.relationship(
        "Complaint", back_populates="category", passive_deletes=True
    )


class Complaint(db.Model):
    __tablename__ = "complaints"

    id = db.Column(ID_TYPE, primary_key=True)
    ticket_id = db.Column(db.String(32), unique=True)
    reporter_id = db.Column(
        ID_TYPE, db.ForeignKey("users.id"), nullable=False
    )
    category_id = db.Column(
        ID_TYPE, db.ForeignKey("categories.id"), nullable=False
    )
    department_id = db.Column(
        ID_TYPE, db.ForeignKey("departments.id"), nullable=True
    )
    assigned_to = db.Column(ID_TYPE, db.ForeignKey("users.id"), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    image_key = db.Column(db.Text)
    priority = db.Column(
        db.String(20), nullable=False, default="Normal", server_default="Normal"
    )
    status = db.Column(
        db.String(20), nullable=False, default="Submitted", server_default="Submitted"
    )
    rejection_reason = db.Column(db.Text)
    resolution_notes = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=db.func.now(),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=db.func.now(),
    )
    resolved_at = db.Column(db.DateTime(timezone=True))

    reporter = db.relationship(
        "User", foreign_keys=[reporter_id], back_populates="complaints"
    )
    assignee = db.relationship("User", foreign_keys=[assigned_to])
    category = db.relationship("Category", back_populates="complaints")
    department = db.relationship("Department", back_populates="complaints")
    history = db.relationship(
        "ComplaintHistory",
        back_populates="complaint",
        order_by="ComplaintHistory.id",
        passive_deletes=True,
    )

    __table_args__ = (
        db.CheckConstraint(
            "priority IN ('Low', 'Normal', 'High', 'Urgent')",
            name="ck_complaints_priority",
        ),
        db.CheckConstraint(
            "status IN ('Submitted', 'In Progress', 'Resolved', 'Rejected', 'Cancelled')",
            name="ck_complaints_status",
        ),
        db.CheckConstraint(
            "status <> 'Rejected' OR rejection_reason IS NOT NULL",
            name="ck_complaints_rejection_reason",
        ),
        db.CheckConstraint(
            "status <> 'Resolved' OR (resolved_at IS NOT NULL AND resolution_notes IS NOT NULL)",
            name="ck_complaints_resolved_completion",
        ),
        db.Index(
            "idx_complaints_reporter_created",
            "reporter_id",
            db.text("created_at DESC"),
        ),
        db.Index("idx_complaints_department_status", "department_id", "status"),
        db.Index("idx_complaints_assigned_to", "assigned_to"),
    )


class ComplaintHistory(db.Model):
    __tablename__ = "complaint_history"

    id = db.Column(ID_TYPE, primary_key=True)
    complaint_id = db.Column(
        ID_TYPE, db.ForeignKey("complaints.id"), nullable=False
    )
    actor_id = db.Column(ID_TYPE, db.ForeignKey("users.id"), nullable=False)
    action = db.Column(db.String(40), nullable=False)
    old_status = db.Column(db.String(20))
    new_status = db.Column(db.String(20))
    remarks = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=db.func.now(),
    )

    complaint = db.relationship("Complaint", back_populates="history")
    actor = db.relationship("User")

    __table_args__ = (
        db.Index("idx_complaint_history_ticket", "complaint_id", "created_at"),
    )


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(ID_TYPE, primary_key=True)
    complaint_id = db.Column(
        ID_TYPE, db.ForeignKey("complaints.id"), nullable=False, unique=True
    )
    rating = db.Column(db.SmallInteger, nullable=False)
    comments = db.Column(db.Text)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=db.func.now(),
    )

    __table_args__ = (
        db.CheckConstraint("rating BETWEEN 1 AND 5", name="ck_feedback_rating"),
    )
