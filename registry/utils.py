"""Helper utilities and decorators."""

import datetime
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

EMAIL_RE = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
# Phone: with country code, or 9 digits starting with 1-9 (not part of longer number)
PHONE_RE = r"(?:\+420|00420)\s?[1-9]\d{2}\s?\d{3}\s?\d{3}|(?<!\d)[1-9]\d{2}\s?\d{3}\s?\d{3}(?!\d)"
# RC: slash format or 9-10 digits (valid)
# This might collide with phone numbers, but it's not a problem because we validate the RC first.
RC_RE = r"\b\d{6}/\d{3,4}\b|\b\d{9,10}\b"


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


def send_email_with_award_doc(to, award_doc_content, medal, config) -> bool:
    msg = EmailMessage()
    msg["From"] = config["EMAIL_SENDER"]
    msg["To"] = to
    msg["Cc"] = config["EMAIL_SENDER"]
    msg["Subject"] = "Ocenění za darování krve a krevních složek"

    msg_first_part = (
        f"Vážení,\n\n"
        f"v letošním roce jste získali {capitalize_first(medal.title_acc)} za {medal.minimum_donations} bezpříspěvkových odběrů krve.\n\n"
        f"Český červený kříž Vám děkuje za tento vysoce lidský a humánní čin.\n\n"
        f"Zasíláme Vám potvrzení o ocenění pro Vašeho zaměstnavatele, případně zdravotní pojišťovnu.\n\n"
    )

    msg_last_part = (
        "Děkujeme.\n"
        "S pozdravem\n"
        "Bc. Michaela Liebelová\n"
        "Ředitelka Úřadu Oblastního spolku ČČK FM\n"
    )

    if medal.slug in ("br", "st"):
        msg_middle_part = f"{capitalize_first(medal.title_acc)}, si prosím vyzvedněte na odběrném místě, kde darujete krev či plazmu.\n\n"
    elif medal.slug in ("zl", "kr3"):
        msg_middle_part = "Předávání ocenění se uskuteční na podzim v Třinci a Frýdku-Místku dle Vašeho odběrného místa. Pozvánka na slavnostní oceňování Vám dorazi s dostatečným předstihem.\n\n"
    elif medal.slug in ("kr2", "kr1", "plk"):
        msg_middle_part = (
            "Pozvánku na slavnostní oceňování obdržíte s dostatečným předstihem.\n\n"
        )

    msg.set_content(msg_first_part + msg_middle_part + msg_last_part)

    msg.add_attachment(
        award_doc_content,
        maintype="application",
        subtype="pdf",
        filename="Potvrzení o udělení medaile.pdf",
    )
    try:
        with smtplib.SMTP(
            config["SMTP_SERVER"], config["SMTP_PORT"], timeout=20
        ) as server:
            server.starttls()
            server.login(config["SMTP_LOGIN"], config["SMTP_PASSWORD"])
            server.send_message(msg)
    # socket.gaierror -> socket.error -> OSerror -> Eception
    except OSError as e:
        flash(f"OSError - {e}", "danger")
        return False
    return True


def get_empty_str_if_none(dictionary, key):
    """Returns empty string if the value for the given key is None"""
    value = dictionary.get(key, "")
    return value if value is not None else ""


def is_valid_rc(value):
    """
    Validates Czech birth number (rodné číslo).
    Supports:
      - 9 digits (pre-1954, no checksum)
      - 10 digits (post-1954, checksum mod 11)

    Accepts formats with or without slash.
    """
    if not isinstance(value, str):
        return False

    # remove slash and spaces
    rc = re.sub(r"[^\d]", "", value)

    if len(rc) not in (9, 10):
        return False

    yy = int(rc[0:2])
    mm = int(rc[2:4])
    dd = int(rc[4:6])

    # adjust month (women +50)
    if mm > 50:
        mm -= 50

    # month validity
    if not 1 <= mm <= 12:
        return False

    # year resolution
    if len(rc) == 9:
        # pre-1954
        year = 1900 + yy
        if year >= 1954:
            return False
    else:
        # 10 digits
        year = 1900 + yy if yy >= 54 else 2000 + yy

    # date validity
    try:
        datetime.date(year, mm, dd)
    except ValueError:
        return False

    # checksum for 10-digit RC
    if len(rc) == 10:
        num = int(rc[:9])
        check = num % 11
        if check == 10:
            check = 0
        if check != int(rc[9]):
            return False

    return True
