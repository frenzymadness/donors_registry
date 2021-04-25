"""The app module, containing the app factory function."""
import logging
import sys

from flask import Flask

from registry import commands, donor, public, user
from registry.extensions import (
    bcrypt,
    csrf_protect,
    db,
    debug_toolbar,
    login_manager,
    migrate,
)
from registry.utils import template_globals


def create_app(config_object="registry.settings"):
    """Create application factory, as explained here:
    http://flask.pocoo.org/docs/patterns/appfactories/.

    :param config_object: The configuration object to use.
    """
    app = Flask(__name__.split(".")[0])
    app.config.from_object(config_object)
    app.context_processor(template_globals)
    register_extensions(app)
    register_blueprints(app)
    register_commands(app)
    configure_logger(app)
    return app


def register_extensions(app):
    """Register Flask extensions."""
    bcrypt.init_app(app)
    db.init_app(app)
    csrf_protect.init_app(app)
    login_manager.init_app(app)
    debug_toolbar.init_app(app)
    migrate.init_app(app, db)
    return None


def register_blueprints(app):
    """Register Flask blueprints."""
    app.register_blueprint(public.views.blueprint)
    app.register_blueprint(user.views.blueprint)
    app.register_blueprint(donor.views.blueprint)
    return None


def register_commands(app):
    """Register Click commands."""
    app.cli.add_command(commands.create_user)
    app.cli.add_command(commands.install_test_data)
    app.cli.add_command(commands.install_production_data)


def configure_logger(app):
    """Configure loggers."""
    handler = logging.StreamHandler(sys.stdout)
    if not app.logger.handlers:
        app.logger.addHandler(handler)
