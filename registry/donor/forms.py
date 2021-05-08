from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, SelectField, TextAreaField
from wtforms.validators import DataRequired

from registry.donor.models import AwardedMedals, Batch
from registry.list.models import DonationCenter

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


class RemoveMedalForm(FlaskForm):
    rodne_cislo = HiddenField(validators=[DataRequired()])
    medal_id = HiddenField(validators=[DataRequired()])

    def validate(self):
        self.awarded_medal = AwardedMedals.query.get(
            (self.rodne_cislo.data, self.medal_id.data)
        )
        return self.awarded_medal is not None


class AwardMedalForm(FlaskForm):
    medal_id = HiddenField(validators=[DataRequired()])

    def add_checkboxes(self, rodna_cisla):
        for rodne_cislo in rodna_cisla:
            name = "rodne_cislo_" + rodne_cislo
            checkbox = BooleanField(_form=self, _name="rodne_cislo", default="checked")
            checkbox.data = rodne_cislo
            setattr(self, name, checkbox)

    def add_one_rodne_cislo(self, rodne_cislo):
        rodne_cislo_input = HiddenField(
            _form=self, _name="rodne_cislo", validators=[DataRequired()]
        )
        rodne_cislo_input.data = rodne_cislo
        setattr(self, "rodne_cislo", rodne_cislo_input)


class NoteForm(FlaskForm):
    rodne_cislo = HiddenField(validators=[DataRequired()])
    note = TextAreaField("Poznámka k dárci")


class DeleteBatchForm(FlaskForm):
    batch_id = HiddenField(validators=[DataRequired()])

    def validate(self):
        self.batch = Batch.query.get(self.batch_id.data)
        return self.batch is not None
