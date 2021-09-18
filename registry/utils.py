"""Helper utilities and decorators."""
import re

from flask import flash
from markupsafe import Markup
from wtforms.validators import DataRequired as OriginalDataRequired
from wtforms.validators import ValidationError


def capitalize(string):
    def get_replacement(match):
        word = match[0]
        if word.isupper():
            return word.capitalize()
        else:
            return word

    return re.sub(r"\w{2,}", get_replacement, string)


def format_postal_code(code: str):
    return code[:3] + Markup("&nbsp;") + code[3:]


def flash_errors(form, category="warning"):
    """Flash all errors for a form."""
    for field, errors in form.errors.items():
        for error in errors:
            flash(f"{getattr(form, field).label.text} - {error}", category)


def template_globals():
    """
    Injected into all templates
     - all medals are needed for the nav bar
    """
    from registry.donor.models import Medals

    all_medals = Medals.query.all()
    return dict(all_medals=all_medals)


class NumericValidator:
    """
    A WTForms validator for validating strings that consist only of digits and are
    exactly of a specified length.
    """

    def __init__(self, length, msg_numeric=None, msg_length=None):
        """
        :param int length: The exact length the field must have
        :param str msg_numeric: An error message for when the field contains forbidden
            characters
        :param str msg_length: An error message for when the field doesn't have
            the specified length
        """
        self.length = length

        if msg_numeric is None:
            msg_numeric = "Pole musí obsahovat pouze číslice"
        if msg_length is None:
            plural = "znaků"
            if length == 1:
                plural = "znak"
            elif length <= 4:
                plural = "znaky"

            msg_length = f"Pole musí mít právě {length} {plural}"

        self.msg_numeric = msg_numeric
        self.msg_length = msg_length

    def __call__(self, form, field):
        if field.data:
            if not field.data.isdigit():
                raise ValidationError(self.msg_numeric)
            if len(field.data) != self.length:
                raise ValidationError(self.msg_length)


class DataRequired(OriginalDataRequired):
    def __init__(self, *args, **kwargs):
        super(OriginalDataRequired, self).__init__(*args, **kwargs)
        self.message = "Toto pole je povinné!"
