from io import BytesIO
import tempfile
import unittest

from PIL import Image
from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import Category, Complaint, ComplaintHistory, Department, User
from app.services.data import (
    create_complaint,
    deactivate_record,
    list_complaints,
)


class CampusAppTests(unittest.TestCase):
    def setUp(self):
        self.upload_dir = tempfile.TemporaryDirectory()
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
                "UPLOAD_FOLDER": self.upload_dir.name,
                "WTF_CSRF_ENABLED": False,
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            department = Department(name="Facilities")
            db.session.add(department)
            db.session.flush()
            category = Category(name="Maintenance", default_department=department)
            student = User(
                name="Student One",
                email="student@example.edu",
                password_hash=generate_password_hash("correct-horse-battery"),
                role="student",
            )
            other_student = User(
                name="Student Two",
                email="other@example.edu",
                password_hash=generate_password_hash("correct-horse-battery"),
                role="student",
            )
            officer = User(
                name="Officer One",
                email="officer@example.edu",
                password_hash=generate_password_hash("correct-horse-battery"),
                role="officer",
                department=department,
            )
            unassigned_officer = User(
                name="Officer Without Department",
                email="unassigned-officer@example.edu",
                password_hash=generate_password_hash("correct-horse-battery"),
                role="officer",
            )
            admin = User(
                name="Admin One",
                email="admin@example.edu",
                password_hash=generate_password_hash("correct-horse-battery"),
                role="admin",
            )
            db.session.add_all(
                [category, student, other_student, officer, unassigned_officer, admin]
            )
            db.session.commit()
            self.student_id = student.id
            self.category_id = category.id

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()
        self.upload_dir.cleanup()

    def test_health_check_does_not_expose_configuration(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"status": "ok"})
        self.assertNotIn(b"DATABASE_URL", response.data)
        self.assertNotIn(b"SECRET_KEY", response.data)

    def test_complaint_service_generates_ticket_from_database_id_and_history(self):
        with self.app.app_context():
            student = db.session.get(User, self.student_id)
            category = db.session.get(Category, self.category_id)
            complaint = create_complaint(
                reporter=student,
                category=category,
                title="Broken light",
                description="The light is not working.",
                location="Block A",
            )
            db.session.commit()

            self.assertEqual(complaint.ticket_id, f"SCG-{complaint.id:08d}")
            self.assertEqual(len(complaint.history), 1)
            self.assertEqual(list_complaints(reporter_id=student.id), [complaint])

    def test_supported_reference_records_are_deactivated_not_deleted(self):
        with self.app.app_context():
            department = db.session.get(Department, 1)
            deactivate_record(department)
            db.session.commit()

            self.assertFalse(db.session.get(Department, department.id).is_active)

    def login(self, email):
        return self.client.post(
            "/login",
            data={"email": email, "password": "correct-horse-battery"},
            follow_redirects=True,
        )

    def complaint_form(self, **updates):
        data = {
            "title": "Broken light",
            "category_id": str(self.category_id),
            "description": "The corridor light is not working.",
            "location": "North hall",
            "priority": "Normal",
        }
        data.update(updates)
        return data

    def test_login_required_and_role_limited_complaints(self):
        response = self.client.get("/complaints")
        self.assertEqual(response.status_code, 302)
        self.login("student@example.edu")
        response = self.client.post("/complaints/new", data=self.complaint_form())
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            complaint = Complaint.query.one()
            self.assertEqual(complaint.ticket_id, f"SCG-{complaint.id:08d}")
            self.assertEqual(complaint.department.name, "Facilities")
            self.assertEqual(complaint.status, "Submitted")
            history = ComplaintHistory.query.filter_by(complaint_id=complaint.id).all()
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0].new_status, "Submitted")

        self.client.post("/logout")
        self.login("other@example.edu")
        self.assertEqual(self.client.get("/complaints/1").status_code, 404)

    def test_submitted_complaint_edit_is_audited(self):
        self.login("student@example.edu")
        self.client.post("/complaints/new", data=self.complaint_form())
        response = self.client.post(
            "/complaints/1/edit",
            data=self.complaint_form(title="Light repaired report"),
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            complaint = db.session.get(Complaint, 1)
            self.assertEqual(complaint.title, "Light repaired report")
            self.assertEqual(ComplaintHistory.query.count(), 2)
            self.assertEqual(
                ComplaintHistory.query.order_by(ComplaintHistory.id).all()[-1].action,
                "Edited",
            )

    def test_complaint_pages_and_valid_image_render(self):
        self.login("student@example.edu")
        image_data = BytesIO()
        Image.new("RGB", (8, 8), color="blue").save(image_data, format="PNG")
        image_data.seek(0)
        response = self.client.post(
            "/complaints/new",
            data=self.complaint_form(image=(image_data, "evidence.png")),
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/complaints").status_code, 200)
        self.assertEqual(self.client.get("/complaints/1").status_code, 200)
        self.assertEqual(self.client.get("/complaints/1/edit").status_code, 200)
        image_response = self.client.get("/complaints/1/image")
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response.mimetype, "image/png")
        image_response.close()

    def test_invalid_image_is_rejected_without_saving_complaint(self):
        self.login("student@example.edu")
        response = self.client.post(
            "/complaints/new",
            data=self.complaint_form(image=(BytesIO(b"not an image"), "bad.png")),
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Upload a valid JPEG, PNG, or WebP image.", response.data)
        with self.app.app_context():
            self.assertEqual(Complaint.query.count(), 0)

    def test_admin_can_manage_reference_data_but_student_cannot(self):
        self.login("student@example.edu")
        self.assertEqual(self.client.get("/admin/").status_code, 403)
        self.client.post("/logout")
        self.login("admin@example.edu")
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        response = self.client.post("/admin/departments", data={"name": "IT"})
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            department = Department.query.filter_by(name="IT").one()
            department_id = department.id

        response = self.client.post(
            "/admin/categories",
            data={"name": "Network", "department_id": str(department_id)},
        )
        self.assertEqual(response.status_code, 302)
        response = self.client.post(
            "/admin/users",
            data={
                "name": "New Officer",
                "email": "new-officer@example.edu",
                "password": "a-long-test-password",
                "role": "officer",
                "department_id": str(department_id),
            },
        )
        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            user = User.query.filter_by(email="new-officer@example.edu").one()
            self.assertNotEqual(user.password_hash, "a-long-test-password")
            user_id = user.id
            category = Category.query.filter_by(name="Network").one()
            category_id = category.id

        self.assertEqual(
            self.client.post(
                f"/admin/categories/{category_id}",
                data={
                    "name": "Networking",
                    "department_id": str(department_id),
                    "is_active": "on",
                },
            ).status_code,
            302,
        )
        self.assertEqual(
            self.client.post(
                f"/admin/users/{user_id}",
                data={
                    "name": "Updated Officer",
                    "email": "new-officer@example.edu",
                    "password": "",
                    "role": "officer",
                    "department_id": str(department_id),
                    "is_active": "on",
                },
            ).status_code,
            302,
        )
        with self.app.app_context():
            self.assertIsNotNone(Category.query.filter_by(name="Networking").first())
            self.assertEqual(
                db.session.get(User, user_id).name, "Updated Officer"
            )

    def test_officer_without_department_cannot_see_unassigned_complaints(self):
        self.login("student@example.edu")
        with self.app.app_context():
            category = Category(name="General")
            db.session.add(category)
            db.session.commit()
            self.category_id = category.id
        self.client.post(
            "/complaints/new",
            data=self.complaint_form(category_id=str(self.category_id)),
        )
        self.client.post("/logout")
        self.login("unassigned-officer@example.edu")
        response = self.client.get("/complaints")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Broken light", response.data)

    def test_passwords_are_hashed_and_invalid_login_fails(self):
        with self.app.app_context():
            user = db.session.get(User, self.student_id)
            self.assertNotEqual(user.password_hash, "correct-horse-battery")
        response = self.client.post(
            "/login",
            data={"email": "student@example.edu", "password": "wrong"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Invalid email or password", response.data)

    def test_csrf_rejects_post_without_token(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        response = self.client.post(
            "/login",
            data={"email": "student@example.edu", "password": "correct-horse-battery"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
