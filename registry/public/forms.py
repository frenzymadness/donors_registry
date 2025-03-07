"""Public forms."""

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField

from registry.user.models import User
from registry.utils import DataRequired


class LoginForm(FlaskForm):
    """Login form."""

    email = StringField("E-mail", validators=[DataRequired()])
    password = PasswordField("Heslo", validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        """Create instance."""
        super(LoginForm, self).__init__(*args, **kwargs)
        self.user = None

    def validate(self, **kwargs):
        """Validate the form."""
        initial_validation = super(LoginForm, self).validate()
        if not initial_validation:
            return False

        self.user = User.query.filter_by(email=self.email.data).first()
        if not self.user:
            self.email.errors.append("Neznámý uživatel")
            return False

        if not self.user.check_password(self.password.data):
            self.password.errors.append("Nesprávné heslo")
            return False

        if not self.user.active:
            self.email.errors.append("Neaktivní uživatel")
            return False
        return True
