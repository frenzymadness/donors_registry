"""Helper utilities and decorators."""
import os
import re
from contextlib import contextmanager
from glob import glob
from pathlib import Path

from flask import flash, url_for
from markupsafe import Markup
from wtforms.validators import DataRequired as OriginalDataRequired
from wtforms.validators import ValidationError

from registry.list.models import Medals


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
    all_medals = Medals.query.all()
    return dict(all_medals=all_medals)


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def get_list_of_images(folder):
    """Returns list of all *.png files from given folder."""
    result = []
    with cd(Path(__file__).parent / "static"):
        for f in glob(f"{folder}/*.png"):
            result.append(url_for("static", filename=f))

    return result


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


# Based on https://eprehledy.cz/ceske_tituly.php
degrees = {
    r"\Wbca\W?": "BcA.",
    r"\Wicdr\W?": "ICDr.",
    r"\Wing\. ?arch\W?": "Ing. arch.",
    r"\Wjudr\W?": "JUDr.",
    r"\Wmddr\W?": "MDDr.",
    r"\Wmga\W?": "MgA.",
    r"\Wmgr\W?": "Mgr.",
    r"\Wmsdr\W?": "MSDr.",
    r"\Wmudr\W?": "MUDr.",
    r"\Wmvdr\W?": "MVDr.",
    r"\Wpaed?dr\W?": "PaedDr.",
    r"\Wpharmdr\W?": "PharmDr.",
    r"\Wphdr\W?": "PhDr.",
    r"\Wphmr\W?": "PhMr.",
    r"\Wrcdr\W?": "RCDr.",
    r"\Wrtdr\W?": "RTDr.",
    r"\Wrndr\W?": "RNDr.",
    r"\Wrsdr\W?": "RSDr.",
    r"\Wthdr\W?": "ThDr.",
    r"\Wthlic\W?": "ThLic.",
    # These three are at the very bottom on purpose
    # because they overlap with some degrees above
    # and we should detect the ones above first.
    r"\Wbc\W?": "Bc.",
    r"\Wdr\W?": "Dr.",
    r"\Wing\W?": "Ing.",
}


def split_degrees(last_name):
    detected_degrees = []
    for regex, correct_form in degrees.items():
        result = re.search(regex, last_name, re.IGNORECASE)
        if result:
            detected_degrees.append(correct_form)
            parts = last_name.split(result.group())
            last_name = " ".join((p.strip() for p in parts))

    return last_name.strip().rstrip(",").strip(), " ".join(detected_degrees)
