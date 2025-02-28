"""Helper utilities and decorators."""

import os
import re
import smtplib
from contextlib import contextmanager
from email.message import EmailMessage
from glob import glob
from pathlib import Path

from flask import flash, url_for
from markupsafe import Markup
from wtforms.validators import DataRequired as OriginalDataRequired
from wtforms.validators import ValidationError

from registry.list.models import DonationCenter, Medals
from registry.settings import (
    EMAIL_SENDER,
    SMTP_LOGIN,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_SERVER,
)

EMAIL_RE = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"


def capitalize(string):
    def get_replacement(match):
        word = match[0]
        if word.isupper():
            return word.capitalize()
        else:
            return word

    return re.sub(r"\w{2,}", get_replacement, string)


def capitalize_first(string):
    return string[0].upper() + string[1:] if string else string


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
    original_last_name = last_name
    detected_degrees = []
    order_by_indexes = []
    for regex, correct_form in degrees.items():
        result = re.search(regex, last_name, re.IGNORECASE)
        if result:
            detected_degrees.append(correct_form)
            parts = last_name.split(result.group())
            last_name = " ".join((p.strip() for p in parts))
            # To be able to order degrees as they were in the original
            # input, we have to get their possition from the original input.
            result = re.search(regex, original_last_name, re.IGNORECASE)
            order_by_indexes.append(result.span()[0])

    last_name_prepared = last_name.strip().rstrip(",").strip()
    degrees_sorted = sorted(
        detected_degrees,
        key=lambda degree: order_by_indexes[detected_degrees.index(degree)],
    )

    return last_name_prepared, " ".join(degrees_sorted)


def record_as_input_data(record, donation_count=None, sum_with_last=False):
    """Takes Record or DonorOverview and prepares it
    as new input data"""

    fields = [
        "rodne_cislo",
        "first_name",
        "last_name",
        "address",
        "city",
        "postal_code",
        "kod_pojistovny",
        "donation_count",
    ]
    values = [str(getattr(record, field)) for field in fields]
    if donation_count:
        if sum_with_last:
            values[-1] = f"{values[-1]}+{donation_count}"
        else:
            values[-1] = donation_count
    line = ";".join(values)
    line += "\r\n"
    return line


def date_of_birth_from_rc(rodne_cislo):
    first, second, third, *rest = [
        rodne_cislo[i : i + 2] for i in range(0, len(rodne_cislo), 2)
    ]

    # YYMMDD/XXXX is a valid format since 1954.
    # If it's shorter, it's more likely from 1900s than 2000s.
    if len(rodne_cislo) == 11 and int(first) < 54:
        year = f"20{first}"
    else:
        year = f"19{first}"

    month = int(second)
    if second[0] in ("2", "3", "5", "6", "7", "8"):
        month -= int(f"{second[0]}0")

    day = int(third)

    return f"{day}. {month}. {year}"


def donor_as_row(donor):
    """Takes donor and returns line with:
    name;surname;date of birth;address;city;postal_code;kod_pojistovny;donation_centers
    """
    donation_centers = DonationCenter.query.order_by(DonationCenter.slug.desc()).all()
    dcs_list = []
    for dc in donation_centers:
        if getattr(donor, f"donation_count_{dc.slug}") > 0:
            dcs_list.append(dc.title)

    result = [
        donor.first_name,
        donor.last_name,
        date_of_birth_from_rc(donor.rodne_cislo),
        donor.address,
        donor.city,
        donor.postal_code,
        donor.kod_pojistovny,
        dcs_list,
    ]

    return result


def send_email_with_award_doc(to, award_doc_content, medal):
    msg = EmailMessage()
    msg["From"] = EMAIL_SENDER
    msg["To"] = to
    msg["Cc"] = EMAIL_SENDER
    msg["Subject"] = "Ocenění za darování krve a krevních složek"

    msg.set_content(
        f"Vážení,\n\n"
        f"v letošním roce jste získali {capitalize_first(medal.title_acc)} za {medal.minimum_donations} bezpříspěvkových odběrů krve.\n\n"
        f"Český červený kříž Vám děkuje za tento vysoce lidský a humánní čin.\n\n"
        f"Zasíláme Vám potvrzení o ocenění pro Vašeho zaměstnavatele, případně zdravotní pojišťovnu.\n\n"
        f"{capitalize_first(medal.title_acc)}, si prosím vyzvedněte na odběrném místě, kde darujete krev či plazmu.\n\n"
        f"Děkujeme.\n"
        f"S pozdravem\n"
        f"Bc. Michaela Liebelová\n"
        f"Ředitelka Úřadu Oblastního spolku ČČK FM\n"
    )

    msg.add_attachment(
        award_doc_content,
        maintype="application",
        subtype="pdf",
        filename="Potvrzení o udělení medaile.pdf",
    )

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_LOGIN, SMTP_PASSWORD)
        server.send_message(msg)
