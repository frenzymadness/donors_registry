"""
Extensions module. Each extension is initialized in the app factory located
in app.py.
"""
import locale
from sqlite3 import Connection as SQLite3Connection

import sqlite_icu
from flask_bcrypt import Bcrypt
from flask_debugtoolbar import DebugToolbarExtension
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

bcrypt = Bcrypt()
csrf_protect = CSRFProtect()
login_manager = LoginManager()
db = SQLAlchemy()
migrate = Migrate()
debug_toolbar = DebugToolbarExtension()


@event.listens_for(Engine, "connect")
def _set_sqlite_params(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        # Create collation for proper sorting
        locale.setlocale(locale.LC_ALL, "cs_CZ.utf8")
        dbapi_connection.create_collation("czech", locale.strcoll)

        # Load SQLite ICU extension for case-insensitive LIKE
        dbapi_connection.enable_load_extension(True)
        dbapi_connection.load_extension(sqlite_icu.extension_path().replace(".so", ""))
        dbapi_connection.enable_load_extension(False)

        # Activate foreign keys
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
