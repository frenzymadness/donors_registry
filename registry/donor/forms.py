from flask import flash
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    HiddenField,
    IntegerField,
    StringField,
    TextAreaField,
)

from registry.donor.models import (
    AwardedMedals,
    DonorsOverride,
    DonorsOverview,
    IgnoredDonors,
    Medals,
)
from registry.extensions import db
from registry.utils import DataRequired, NumericValidator


class RemoveMedalForm(FlaskForm):
    rodne_cislo = HiddenField(validators=[DataRequired()])
    medal_id = HiddenField(validators=[DataRequired()])

    def validate(self, **kwargs):
        self.awarded_medal = db.session.get(
            AwardedMedals, (self.rodne_cislo.data, self.medal_id.data)
        )
        return self.awarded_medal is not None


class AwardMedalForm(FlaskForm):
    medal_id = HiddenField(validators=[DataRequired()])

    def add_checkboxes(self, rodna_cisla):
        for rodne_cislo in rodna_cisla:
            name = "rodne_cislo_" + rodne_cislo
            checkbox = BooleanField(_form=self, name="rodne_cislo", default="checked")
            checkbox.data = rodne_cislo
            setattr(self, name, checkbox)

    def add_one_rodne_cislo(self, rodne_cislo):
        rodne_cislo_input = HiddenField(
            _form=self, name="rodne_cislo", validators=[DataRequired()]
        )
        rodne_cislo_input.data = rodne_cislo
        setattr(self, "rodne_cislo_" + rodne_cislo, rodne_cislo_input)

    def validate(self, **kwargs):
        self.medal = db.session.get(Medals, self.medal_id.data)

        if self.medal is None:
            flash("Odeslána nevalidní data.", "danger")
            return False

        self.overviews = {}
        for rodne_cislo in self.rodna_cisla:
            do = db.session.get(DonorsOverview, rodne_cislo)
            if do:
                self.overviews[rodne_cislo] = do
            else:
                flash("Odeslána nevalidní data.", "danger")
                return False

        return True


class NoteForm(FlaskForm):
    rodne_cislo = HiddenField(validators=[DataRequired()])
    note = TextAreaField("Poznámka k dárci")


class IgnoreDonorForm(FlaskForm):
    rodne_cislo = StringField("Rodné číslo", validators=[DataRequired()])
    reason = StringField("Důvod k ignoraci", validators=[DataRequired()])


class RemoveFromIgnoredForm(FlaskForm):
    rodne_cislo = HiddenField(validators=[DataRequired()])

    def validate(self, **kwargs):
        self.ignored_donor = db.session.get(IgnoredDonors, self.rodne_cislo.data)
        return self.ignored_donor is not None


class DonorsOverrideForm(FlaskForm):
    rodne_cislo = StringField("Rodné číslo", validators=[DataRequired()])
    first_name = StringField("Jméno")
    last_name = StringField("Příjmení")
    address = StringField("Adresa")
    city = StringField("Město")
    postal_code = StringField("PSČ", validators=[NumericValidator(5)])
    kod_pojistovny = StringField("Pojišťovna", validators=[NumericValidator(3)])

    def init_fields(self, rodne_cislo):
        override = db.session.get(DonorsOverride, rodne_cislo)

        if override is not None:
            for field in DonorsOverview.basic_fields:
                data = getattr(override, field)
                if data is not None:
                    getattr(self, field).data = data

        self.rodne_cislo.data = rodne_cislo

    def get_field_data(self):
        field_data = {}
        for field in DonorsOverview.basic_fields:
            field_data[field] = getattr(self, field).data or None

        return field_data


class PrintEnvelopeLabelsForm(FlaskForm):
    medal_id = HiddenField(validators=[DataRequired()])
    skip = IntegerField(validators=[DataRequired()])

    def validate(self, **kwargs):
        self.medal = db.session.get(Medals, self.medal_id.data)

        if self.medal is None:
            flash("Odeslána nevalidní data.", "danger")
            return False

        if self.skip.data is None:
            self.skip.data = 0

        if not (0 <= self.skip.data < 16):
            flash("Vynechat lze 0 až 15 štítků.", "danger")
            return False

        return True
