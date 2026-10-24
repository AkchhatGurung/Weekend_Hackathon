import os

import click
from flask import Flask, jsonify, flash, redirect, render_template, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.security import generate_password_hash

from config import Config
from app.extensions import csrf, db, login_manager, migrate
from app.constants import MIN_PASSWORD_LENGTH


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("Set SECRET_KEY in the environment before starting the app.")
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("Set DATABASE_URL in the environment before starting the app.")

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    csrf.init_app(app)

    from app import models
    from app.auth import auth_bp
    from app.complaints import complaints_bp
    from app.management import management_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(management_bp)

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.get("/")
    def index():
        return redirect(url_for("complaints.list_complaints"))

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash("Your form session expired. Please try again.", "error")
        return render_template("error.html", message=error.description), 400

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(name, email, password):
        """Create the first administrator account."""
        from app.models import User

        if len(password) < MIN_PASSWORD_LENGTH:
            raise click.ClickException(
                f"Passwords must be at least {MIN_PASSWORD_LENGTH} characters long."
            )
        normalized_email = email.strip().lower()
        if User.query.filter_by(email=normalized_email).first():
            raise click.ClickException("A user with that email already exists.")
        admin = User(
            name=name.strip(),
            email=normalized_email,
            password_hash=generate_password_hash(password),
            role="admin",
        )
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Administrator account created for {normalized_email}.")

    @app.cli.command("seed-data")
    def seed_data():
        """Seed the standard campus departments and categories."""
        from scripts.seed import seed

        seed()
        click.echo("Campus departments and categories seeded.")

    return app
