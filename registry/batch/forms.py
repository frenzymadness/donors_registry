from flask_wtf import FlaskForm

from wtforms import HiddenField, SelectField, TextAreaField
from wtforms.validators import DataRequired

from registry.donor.models import Batch, DonationCenter

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
        self.donation_center_id.choices = [
            (dc.id, dc.title) for dc in DonationCenter.query.all()
        ] + [(-1, "Manuální import nebo data odjinud")]
        self.reset_validator()

    def reset_validator(self):
        self.valid_lines_content, self.invalid_lines_content = None, None

    def validate(self):
        """Validate the form."""
        initial_validation = super(ImportForm, self).validate()
        if not initial_validation:
            return False

        self.reset_validator()

        self.donation_center = DonationCenter.query.get(self.donation_center_id.data)
        if not self.donation_center and int(self.donation_center_id.data) != -1:
            self.donation_center_id.errors.append("Odběrné místo neexistuje")
            return False

        if self.valid_lines.data or self.invalid_lines.data:
            # repeated import with hopefully fixed errors
            # we have to cobine valid and invalid/fixed lines and check them again
            input_data = "\n".join([self.valid_lines.data, self.invalid_lines.data])
            self.valid_lines_content, self.invalid_lines_content = validate_import_data(
                input_data
            )
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

        return True


class DeleteBatchForm(FlaskForm):
    batch_id = HiddenField(validators=[DataRequired()])

    def validate(self):
        self.batch = Batch.query.get(self.batch_id.data)
        return self.batch is not None
