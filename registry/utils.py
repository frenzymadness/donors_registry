"""Helper utilities and decorators."""
from flask import flash
from wtforms.validators import ValidationError

from registry.donor.models import Medals


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
