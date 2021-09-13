import pytest
from wtforms.validators import ValidationError

from registry.utils import NumericValidator

from .helpers import FakeForm


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
