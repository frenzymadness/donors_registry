import pytest
from flask import url_for
from wtforms.validators import ValidationError

from registry.donor.models import DonorsOverview
from registry.utils import NumericValidator

from .helpers import FakeForm, login


class TestNumericValidator:
    def test_length_validation(self):
        validator = NumericValidator(5)
        form = FakeForm()

        form.field.data = "12345"
        validator(form, form.field)

        form.field.data = "11111111111"
        with pytest.raises(ValidationError, match="^Pole musí mít právě 5 znaků$"):
            validator(form, form.field)

        form.field.data = "0"
        with pytest.raises(ValidationError, match="^Pole musí mít právě 5 znaků$"):
            validator(form, form.field)

    def test_numeric_validation(self):
        validator = NumericValidator(5)
        form = FakeForm()

        form.field.data = "12345"
        validator(form, form.field)

        form.field.data = "1234a"
        with pytest.raises(
            ValidationError, match="^Pole musí obsahovat pouze číslice$"
        ):
            validator(form, form.field)

        form.field.data = "0x123"
        with pytest.raises(
            ValidationError, match="^Pole musí obsahovat pouze číslice$"
        ):
            validator(form, form.field)

    def test_messages(self):
        validator = NumericValidator(5, msg_numeric="numeric", msg_length="length")
        form = FakeForm()

        form.field.data = "abcde"
        with pytest.raises(ValidationError, match="^numeric$"):
            validator(form, form.field)

        form.field.data = "1"
        with pytest.raises(ValidationError, match="^length$"):
            validator(form, form.field)

    def test_plural(self):
        form = FakeForm()
        form.field.data = "11111111111"

        validator = NumericValidator(5)
        with pytest.raises(ValidationError, match="^Pole musí mít právě 5 znaků$"):
            validator(form, form.field)

        validator = NumericValidator(3)
        with pytest.raises(ValidationError, match="^Pole musí mít právě 3 znaky$"):
            validator(form, form.field)

        validator = NumericValidator(1)
        with pytest.raises(ValidationError, match="^Pole musí mít právě 1 znak$"):
            validator(form, form.field)


class TestCapitalizer:
    @pytest.mark.parametrize(
        ("input", "expected"),
        (
            ("karlov", "karlov"),
            ("Karlov", "Karlov"),
            ("KARLOV", "Karlov"),
            ("Velké KARLOVICE", "Velké Karlovice"),
            ("velké karlovice", "velké karlovice"),
            ("VELKÉ karlovice", "Velké karlovice"),
            ("VELKÉ KARLOVICE", "Velké Karlovice"),
            ("a b c d", "a b c d"),
            ("A B C D", "A B C D"),
            ("a B c D", "a B c D"),
            ("U LÍPY", "U Lípy"),
            ("u lípy", "u lípy"),
            ("U Lípy", "U Lípy"),
            ("Frýdlant nad Ostravicí", "Frýdlant nad Ostravicí"),
            ("FRÝDLANT NAD OSTRAVICÍ", "Frýdlant Nad Ostravicí"),
        ),
    )
    def test_capitalize(self, testapp, input, expected):
        capitalize = testapp.app.jinja_env.filters["capitalize"]
        output = capitalize(input)
        assert output == expected

    def test_capitalize_in_templates(self, user, testapp, db):
        rodne_cislo = "1234567890"
        do = DonorsOverview(
            rodne_cislo=rodne_cislo,
            first_name="KAREL",
            last_name="VOMÁČKA",
            address="LIPOVÁ 33",
            city="OSTRAVA",
            postal_code="71600",
            kod_pojistovny="213",
            donation_count_fm=50,
            donation_count_fm_bubenik=50,
            donation_count_trinec=50,
            donation_count_mp=50,
            donation_count_manual=50,
            donation_count_total=250,
            awarded_medal_br=False,
            awarded_medal_st=False,
            awarded_medal_zl=False,
            awarded_medal_kr3=False,
            awarded_medal_kr2=False,
            awarded_medal_kr1=False,
            awarded_medal_plk=False,
        )

        db.session.add(do)
        db.session.commit()

        login(user, testapp)

        pages = (
            ("donor.detail", {"rc": rodne_cislo}),
            ("donor.award_prep", {"medal_slug": "br"}),
            ("donor.render_award_document", {"rc": rodne_cislo, "medal_slug": "br"}),
        )

        for page, params in pages:
            res = testapp.get(url_for(page, **params))
            assert "KAREL" not in res
            assert "VOMÁČKA" not in res
            assert "Karel" in res
            assert "Vomáčka" in res
            if "award_document" not in page:
                assert "LIPOVÁ 33" not in res
                assert "OSTRAVA" not in res
                assert "Lipová 33" in res
                assert "Ostrava" in res
