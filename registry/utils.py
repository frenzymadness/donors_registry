"""Helper utilities and decorators."""
from flask import flash

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
