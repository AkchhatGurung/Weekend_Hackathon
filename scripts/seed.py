from app import create_app, db
from app.services.data import create_category, create_department
from app.models import Category, Department


DEPARTMENTS = (
    "Facilities",
    "Information Technology",
    "Student Affairs",
    "Library",
    "Security",
)

CATEGORIES = {
    "Facilities": ("Maintenance", "Cleaning", "Electrical"),
    "Information Technology": ("Network", "Computer Lab"),
    "Student Affairs": ("Academic", "Hostel"),
    "Library": ("Library Services",),
    "Security": ("Campus Safety",),
}


def seed():
    app = create_app()
    with app.app_context():
        departments = {}
        for name in DEPARTMENTS:
            department = db.session.scalar(
                db.select(Department).where(Department.name == name)
            )
            departments[name] = department or create_department(name)
        for department_name, category_names in CATEGORIES.items():
            for category_name in category_names:
                exists = db.session.scalar(
                    db.select(Category).where(Category.name == category_name)
                )
                if not exists:
                    create_category(category_name, departments[department_name])
        db.session.commit()


if __name__ == "__main__":
    seed()
