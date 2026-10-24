# Smart Campus Complaint and Grievance Management System

Phase 1 provides a Flask application factory, Flask-SQLAlchemy, Flask-Migrate,
Flask-Login, CSRF protection, login and role checks, complaint
submission/list/detail/edit, admin maintenance for users/departments/categories,
password hashing, image validation, and complaint history records for
submissions and edits.

Complaint status transitions, feedback and analytics are not implemented in this phase. Complaints are not physically deleted because their history is retained as an audit record. Users, departments and categories can be deactivated.

## Requirements

- Python 3.10 or newer
- PostgreSQL

## Local setup (PowerShell)

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

$env:SECRET_KEY = "replace-with-a-long-random-secret"
$env:DATABASE_URL = "postgresql+psycopg://postgres:password@localhost:5432/smart_campus"
$env:FLASK_APP = "app:create_app"

python -m flask db upgrade
python -m flask create-admin
python -m flask run
```

Create an empty PostgreSQL database before applying the checked-in initial migration with `flask db upgrade`. Use `flask db migrate -m "Describe schema change"` for later model changes, review the generated revision, then apply it with `flask db upgrade`. Keep `SECRET_KEY`, database credentials, and production upload configuration in environment variables, not source control. Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS. `UPLOAD_FOLDER` defaults to an `uploads` directory in the project root.

Seed the standard campus departments and categories after migrations:

```powershell
python -m flask seed-data
```

Reusable data operations are in `app/services/data.py`. Complaint creation
uses the database-generated primary-key sequence to derive ticket IDs, so
concurrent submissions do not depend on row counts.

The `smart_campus_grievance_schema.sql` file is the shared reference schema. For a new database, use the migrations generated from the Flask models rather than running both that starter SQL and migrations.

## Phase 1 routes

- `GET /health`

- `GET /login`, `POST /login`, `POST /logout`
- `GET /complaints`, `GET|POST /complaints/new`
- `GET /complaints/<id>`, `GET|POST /complaints/<id>/edit`
- `GET /complaints/<id>/image`
- `GET /admin`
- `POST /admin/departments`, `POST /admin/departments/<id>`
- `POST /admin/categories`, `POST /admin/categories/<id>`
- `POST /admin/users`, `POST /admin/users/<id>`

Students and staff can access their own complaints; officers can access complaints assigned to their department; administrators can access all complaints and manage reference data and accounts. Complaint editing is limited to its reporter while status is `Submitted`. Status changes are intentionally reserved for the workflow phase.

## Tests

Run the focused test suite with:

```powershell
python -m unittest discover -s tests -v
```

For local testing, user passwords must be at least 3 characters long. Use a
stronger password outside local testing.

## Frontend preview

Start the app with the local environment above and open `http://127.0.0.1:5000/login`. Sign in with the administrator created by `flask create-admin` to preview the administration screens. To preview the complaint list and submission form, create a department and category in Administration, create a student or staff account, then sign in with that account. The complaint list shows its designed empty state until a complaint is submitted; the interface does not seed or hardcode user or complaint records.

The shared layout and navigation are in `app/templates/base.html`; page templates are grouped under `auth/`, `complaints/`, and `admin/`. Reusable responsive styles are in `app/static/style.css`, with progressive-enhancement navigation, dismissible notices, and form submission feedback in `app/static/app.js`.
