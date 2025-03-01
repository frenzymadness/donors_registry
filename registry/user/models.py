"""User models."""

import datetime as dt

from flask_login import UserMixin

from registry.extensions import bcrypt, db


class User(UserMixin, db.Model):
    """A user of the app."""

    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(
        db.String(80),
        unique=True,
        nullable=False,
    )
    password = db.Column(db.LargeBinary(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=dt.datetime.utcnow)
    active = db.Column(db.Boolean(), default=False)

    def __init__(self, email, password=None, **kwargs):
        """Create instance."""
        self.email = email
        self.set_password(password)

    def set_password(self, password):
        """Set password."""
        self.password = bcrypt.generate_password_hash(password)

    def check_password(self, value):
        """Check password."""
        return bcrypt.check_password_hash(self.password, value)

    def __repr__(self):
        """Represent instance as a unique string."""
        return f"<User({self.email!r})>"
