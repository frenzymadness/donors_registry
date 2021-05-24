from flask_wtf import FlaskForm
from wtforms import BooleanField, HiddenField, IntegerField, StringField, TextAreaField
from wtforms.validators import DataRequired

from registry.donor.models import AwardedMedals


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


class IgnoreDonorForm(FlaskForm):
    rodne_cislo = IntegerField("Rodné číslo", validators=[DataRequired()])
    reason = StringField("Důvod k ignoraci", validators=[DataRequired()])
