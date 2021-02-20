"""Commands for CLI"""
import click
from flask import current_app
from flask.cli import with_appcontext

from production_data import check_results, load_database, load_text_backups
from registry.donor.models import DonorsOverview
from registry.extensions import db
from registry.user.models import User
from tests.utils import (
    test_data_ignored,
    test_data_medals,
    test_data_overrides,
    test_data_records,
)


@click.command()
@click.argument("email")
@click.argument("password")
@with_appcontext
def create_user(email, password):
    """Create Flask user for given email and password."""
    user = User(email, password)
    user.active = True
    db.session.add(user)
    db.session.commit()


@click.command()
@click.option("--limit", default=None)
@with_appcontext
def install_test_data(limit):
    """Install test data from files to database."""
    # Turn off SQLAlchemy logging (produces thousands of SQL queries)
    current_app.config["SQLALCHEMY_ECHO"] = False

    test_data_records(db, limit=int(limit) if limit else None)
    test_data_medals(db)
    test_data_ignored(db)
    test_data_overrides(db)
    DonorsOverview.refresh_overview()


@click.command("refresh-overview")
@with_appcontext
def refresh_overview():
    """Refresh DonorsOverview table."""
    DonorsOverview.refresh_overview()


@click.command()
@click.argument("path_to_backup")
@click.argument("step", required=False)
@with_appcontext
def install_production_data(path_to_backup, step=None):
    # Turn off SQLAlchemy logging (produces thousands of SQL queries)
    current_app.config["SQLALCHEMY_ECHO"] = False
    if step is None or step == "1":
        load_text_backups(path_to_backup)
    if step is None or step == "2":
        load_database(path_to_backup)
    if step is None or step == "3":
        DonorsOverview.refresh_overview()
    if step is None or step == "4":
        check_results(path_to_backup)
