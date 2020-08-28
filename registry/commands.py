"""Commands for CLI"""
import click
from flask import Flask

from registry.extensions import db
from registry.user.models import User

app = Flask(__name__)


@app.cli.command("create-user")
@click.argument("email")
@click.argument("password")
def create_user(email, password):
    user = User(email, password)
    user.active = True
    db.session.add(user)
    db.session.commit()
