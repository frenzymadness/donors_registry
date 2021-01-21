"""Commands for CLI"""
import click
from flask import current_app
from flask.cli import with_appcontext

from registry.donor.models import DonorsOverview
from registry.extensions import db
from registry.user.models import User
from tests.utils import test_data_medals, test_data_records


@click.command()
@click.argument("email")
@click.argument("password")
@with_appcontext
def create_user(email, password):
    user = User(email, password)
    user.active = True
    db.session.add(user)
    db.session.commit()


@click.command()
@with_appcontext
def install_test_data():
    # Turn off SQLAlchemy logging (produces thousands of SQL queries)
    current_app.config["SQLALCHEMY_ECHO"] = False

    test_data_records(db)
    test_data_medals(db)
    DonorsOverview.refresh_overview()
