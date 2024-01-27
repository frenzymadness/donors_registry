from flask_wtf import FlaskForm
from wtforms import HiddenField, SelectField, TextAreaField

from registry.donor.models import Batch, DonationCenter
from registry.extensions import db
from registry.utils import DataRequired

from .utils import validate_import_data


class ImportForm(FlaskForm):
    donation_center_id = SelectField(
        "Odběrné místo",
        choices=[],
        validators=[DataRequired()],
    )
    input_data = TextAreaField("Vstupní data z odběrného místa")
    valid_lines = TextAreaField("Bezchybná vstupní data")
    invalid_lines = TextAreaField("Vstupní data s chybami")
    invalid_lines_errors = TextAreaField("Chyby ve vstupních datech")

    def __init__(self, *args, **kwargs):
        super(ImportForm, self).__init__(*args, **kwargs)
        self.donation_center_id.choices = [("", "")]
        self.donation_center_id.choices += [
            (dc.id, dc.title) for dc in DonationCenter.query.all()
        ]
        self.donation_center_id.choices += [(-1, "Manuální import nebo data odjinud")]
        self.reset_validator()

    def reset_validator(self):
        self.valid_lines_content, self.invalid_lines_content = None, None
        self.invalid_lines_errors.data = ""

    def validate(self, **kwargs):
        """Validate the form."""
        initial_validation = super(ImportForm, self).validate()
        if not initial_validation:
            return False

        self.reset_validator()

        repeated_import = False
        if self.valid_lines.data or self.invalid_lines.data:
            # repeated import with hopefully fixed errors
            # we have to cobine valid and invalid/fixed lines and check them again
            input_data = "\n".join([self.valid_lines.data, self.invalid_lines.data])
            self.valid_lines_content, self.invalid_lines_content = validate_import_data(
                input_data
            )
            repeated_import = True
        elif self.input_data.data:
            # First import, we have to process input data
            self.valid_lines_content, self.invalid_lines_content = validate_import_data(
                self.input_data.data
            )

        if self.invalid_lines_content:
            self.valid_lines.data = "\n".join(self.valid_lines_content)
            self.invalid_lines.data = ""
            self.invalid_lines_errors.data = ""
            for line, errors in self.invalid_lines_content:
                self.invalid_lines.data += line + "\n"
                self.invalid_lines_errors.data += ", ".join(errors) + "\n"
            return False

        # Empty input would cause errors
        if (
            repeated_import
            and not self.valid_lines.data
            and not self.invalid_lines.data
        ) or (not repeated_import and not self.input_data.data):
            self.input_data.errors.append("Chybí vstupní data")
            return False

        if not self.valid_lines_content and not self.invalid_lines_content:
            self.input_data.errors.append(
                "Ze vstupních dat není po filtraci co importovat"
            )
            return False

        return True


class DeleteBatchForm(FlaskForm):
    batch_id = HiddenField(validators=[DataRequired()])

    def validate(self, **kwargs):
        self.batch = db.session.get(Batch, self.batch_id.data)
        return self.batch is not None
