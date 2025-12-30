import pytest
from flask import url_for
from wtforms.validators import ValidationError

from registry.donor.models import DonorsOverview
from registry.list.models import DonationCenter
from registry.utils import (
    NumericValidator,
    date_of_birth_from_rc,
    donor_as_row,
    is_valid_rc,
    split_degrees,
)

from .fixtures import sample_of_rc
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


class TestDegreeSplitter:
    @pytest.mark.parametrize(
        ("input", "expected_degrees", "expected_last_name"),
        (
            # Test data based on real data from production database
            ("surname -", "", "surname -"),
            ("surname,", "", "surname"),
            ("surname    bc.", "Bc.", "surname"),
            ("surname  bc", "Bc.", "surname"),
            ("surname  bc.", "Bc.", "surname"),
            ("surname bc", "Bc.", "surname"),
            ("surname bc.", "Bc.", "surname"),
            ("surname,bc", "Bc.", "surname"),
            ("surname,bc.", "Bc.", "surname"),
            ("surname,Bc.", "Bc.", "surname"),
            ("surname    BC.", "Bc.", "surname"),
            ("surname  BC", "Bc.", "surname"),
            ("surname  BC.", "Bc.", "surname"),
            ("surname BC", "Bc.", "surname"),
            ("surname BC.", "Bc.", "surname"),
            ("surname   dis.", "", "surname   dis."),
            ("surname  dis", "", "surname  dis"),
            ("surname  dis.", "", "surname  dis."),
            ("surname dis", "", "surname dis"),
            ("surname dis.", "", "surname dis."),
            ("surname,dis", "", "surname,dis"),
            ("surname,dis.", "", "surname,dis."),
            ("surname  DIS", "", "surname  DIS"),
            ("surname  DIS.", "", "surname  DIS."),
            ("surname DIS.", "", "surname DIS."),
            ("surname dis.bc.", "Bc.", "surname dis"),
            ("surname    ing.", "Ing.", "surname"),
            ("surname   ing", "Ing.", "surname"),
            ("surname   ing.", "Ing.", "surname"),
            ("surname  ing", "Ing.", "surname"),
            ("surname  ing.", "Ing.", "surname"),
            ("surname ing", "Ing.", "surname"),
            ("surname ing.", "Ing.", "surname"),
            ("surname, ing.", "Ing.", "surname"),
            ("surname,ing", "Ing.", "surname"),
            ("surname,ing.", "Ing.", "surname"),
            ("surname ,Ing.", "Ing.", "surname"),
            ("surname,Ing.", "Ing.", "surname"),
            ("surname   ING.", "Ing.", "surname"),
            ("surname  ING", "Ing.", "surname"),
            ("surname  ING.", "Ing.", "surname"),
            ("surname ING", "Ing.", "surname"),
            ("surname ING.", "Ing.", "surname"),
            ("surname judr", "JUDr.", "surname"),
            ("surname,judr.", "JUDr.", "surname"),
            ("surname,mba.", "", "surname,mba."),
            ("surname  mgr", "Mgr.", "surname"),
            ("surname  mgr.", "Mgr.", "surname"),
            ("surname mgr", "Mgr.", "surname"),
            ("surname mgr.", "Mgr.", "surname"),
            ("surname,mgr", "Mgr.", "surname"),
            ("surname,mgr.", "Mgr.", "surname"),
            ("surname,Mgr.", "Mgr.", "surname"),
            ("surname   MGR", "Mgr.", "surname"),
            ("surname  MGR", "Mgr.", "surname"),
            ("surname  MGR.", "Mgr.", "surname"),
            ("surname MGR", "Mgr.", "surname"),
            ("surname MGR.", "Mgr.", "surname"),
            ("surname  mgr.phd.", "Mgr.", "surname phd."),
            ("surname,msc.", "", "surname,msc."),
            ("surname mudr", "MUDr.", "surname"),
            ("surname mudr.", "MUDr.", "surname"),
            ("surname,mudr.", "MUDr.", "surname"),
            ("surname MUDR.", "MUDr.", "surname"),
            ("surname  mvdr.", "MVDr.", "surname"),
            ("surname paeddr.", "PaedDr.", "surname"),
            ("surname,paeddr.", "PaedDr.", "surname"),
            ("surname PAEDDR.", "PaedDr.", "surname"),
            ("surname,pharmdr.", "PharmDr.", "surname"),
            ("surname ph.d.", "", "surname ph.d."),
            ("surname,phdr.", "PhDr.", "surname"),
            ("surname rndr.", "RNDr.", "surname"),
            ("surname,rndr.", "RNDr.", "surname"),
            # Incorrect degrees we can fix
            ("surname paedr.", "PaedDr.", "surname"),
            ("surname,paedr.", "PaedDr.", "surname"),
            ("surname PAEDR.", "PaedDr.", "surname"),
            ("surname ing.arch", "Ing. arch.", "surname"),
            ("surname ing. arch.", "Ing. arch.", "surname"),
            # What if a degree is in the middle of the name?
            ("Kipling", "", "Kipling"),
            ("Mgrágová", "", "Mgrágová"),
            ("Sambca", "", "Sambca"),
            ("Mudrc", "", "Mudrc"),
            ("Kipling phmr", "PhMr.", "Kipling"),
            ("Mgrágová,bCa.", "BcA.", "Mgrágová"),
            ("Sambca,mddr", "MDDr.", "Sambca"),
            ("Mudrc rtdr.", "RTDr.", "Mudrc"),
            # The order of the result has to respect
            # the order of the input. No arbitrary sorting here.
            ("surname ing.mgr.", "Ing. Mgr.", "surname"),
            ("surname mgr.ing.", "Mgr. Ing.", "surname"),
            ("surname,ing.phdr.", "Ing. PhDr.", "surname"),
            ("surname,phdr.ing", "PhDr. Ing.", "surname"),
        ),
    )
    def test_split_degree(self, input, expected_degrees, expected_last_name):
        last_name, detected_degrees = split_degrees(input)
        assert detected_degrees == expected_degrees
        assert last_name == expected_last_name


class TestUnit:
    @pytest.mark.parametrize(
        ("rodne_cislo", "expected"),
        (
            ("885512/1234", "12. 5. 1988"),
            ("970331/5678", "31. 3. 1997"),
            ("045624/9876", "24. 6. 2004"),
            ("801210/3456", "10. 12. 1980"),
            ("631015/8765", "15. 10. 1963"),
            ("890820/2345", "20. 8. 1989"),
            ("741201/6543", "1. 12. 1974"),
            ("521113/432", "13. 11. 1952"),
            ("380712/789", "12. 7. 1938"),
            ("071224/8765", "24. 12. 2007"),
            ("670502/5678", "2. 5. 1967"),
            ("931213/3456", "13. 12. 1993"),
            ("200824/654", "24. 8. 1920"),
            ("580716/2345", "16. 7. 1958"),
            ("490608/4321", "8. 6. 2049"),
            ("060307/7890", "7. 3. 2006"),
            ("810401/8765", "1. 4. 1981"),
            ("410918/5678", "18. 9. 2041"),
            ("730520/3456", "20. 5. 1973"),
            ("350714/6543", "14. 7. 2035"),
            ("050714/654", "14. 7. 1905"),
        ),
    )
    def test_date_of_birth_from_rc(self, rodne_cislo, expected):
        assert date_of_birth_from_rc(rodne_cislo) == expected

    @pytest.mark.parametrize("rodne_cislo", sample_of_rc(10))
    def test_donor_as_row(self, rodne_cislo):
        donor = DonorsOverview.query.get(rodne_cislo)
        row = donor_as_row(donor)

        donation_centers = DonationCenter.query.order_by(
            DonationCenter.slug.desc()
        ).all()

        assert donor.first_name == row[0]
        assert donor.last_name == row[1]
        assert donor.address == row[3]

        for dc in donation_centers:
            if getattr(donor, f"donation_count_{dc.slug}") > 0:
                assert dc.title in row[-1]
            else:
                assert dc.title not in row[-1]

    @pytest.mark.parametrize(
        "rc",
        (
            "12345678",
            "12345678901",
            1234567890,
            None,
            "770101123",
            "510229123",
            "8502287014",
            "8502289285",
        ),
    )
    def test_is_valid_rc_negative(self, rc):
        assert not is_valid_rc(rc)
