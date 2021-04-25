"""Commands for CLI"""
import click
from flask import current_app
from flask.cli import with_appcontext

from production_data import check_results, load_database, load_text_backups
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


@click.command()
@click.argument("path_to_backup")
@click.argument("step", required=False)
@with_appcontext
def install_production_data(path_to_backup, step=None):
    # Turn off SQLAlchemy logging (produces thousands of SQL queries)
    current_app.config["SQLALCHEMY_ECHO"] = False
    csv_errors = []
    if step is None or step == "1":
        load_text_backups(path_to_backup)
    if step is None or step == "2":
        csv_errors += load_database(path_to_backup)
    if step is None or step == "3":
        DonorsOverview.refresh_overview()
    if step is None or step == "4":
        csv_errors += check_results(path_to_backup)

    print("\n".join(csv_errors))
