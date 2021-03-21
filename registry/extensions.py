"""
Extensions module. Each extension is initialized in the app factory located
in app.py.
"""
from sqlite3 import Connection as SQLite3Connection

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
def _set_sqlite_pragma(dbapi_connection, connection_record):
    if isinstance(dbapi_connection, SQLite3Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()
