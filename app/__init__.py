import os

import click
from flask import Flask, flash, redirect, render_template, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFError, CSRFProtect
from werkzeug.security import generate_password_hash

from config import Config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()


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
    csrf.init_app(app)

    from app import models
    from app.auth import auth_bp
    from app.complaints import complaints_bp
    from app.management import management_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(complaints_bp)
    app.register_blueprint(management_bp)

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

        if len(password) < 12:
            raise click.ClickException("Passwords must be at least 12 characters long.")
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

    return app
