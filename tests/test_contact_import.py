"""Tests for contact import functionality."""

import re
from io import BytesIO

import pytest
from flask import url_for
from openpyxl import Workbook

from registry.batch.utils import (
    convert_csv_to_text,
    convert_xlsx_to_text,
    parse_contact_line,
    process_contact_import_line,
    validate_contact_import_data,
)
from registry.donor.models import Note
from registry.extensions import db
from registry.utils import EMAIL_RE, PHONE_RE, RC_RE, is_valid_rc

from .fixtures import delete_note_if_exists, new_rc_if_ignored, sample_of_rc
from .helpers import login


class TestRegexPatterns:
    """Test regex patterns for email, phone, and rodne cislo detection."""

    @pytest.mark.parametrize(
        ("text", "expected_emails"),
        (
            ("jan.novak@seznam.cz", ["jan.novak@seznam.cz"]),
            ("kontakt: marie.nova@gmail.com další text", ["marie.nova@gmail.com"]),
            ("dva@email.cz a tri@test.com", ["dva@email.cz", "tri@test.com"]),
            ("petr_123@email.co.uk", ["petr_123@email.co.uk"]),
            ("email bez tečky", []),
            ("špatný@email", []),
            ("info+tag@example.com", ["info+tag@example.com"]),
        ),
    )
    def test_email_regex(self, text, expected_emails):
        """Test EMAIL_RE pattern matches valid emails."""
        matches = re.findall(EMAIL_RE, text)
        assert matches == expected_emails

    @pytest.mark.parametrize(
        ("text", "expected_phones"),
        (
            ("+420 602 123 456", ["+420 602 123 456"]),
            ("+420602123456", ["+420602123456"]),
            ("00420 734 000 000", ["00420 734 000 000"]),
            ("602123456", ["602123456"]),
            ("734 000 000", ["734 000 000"]),
            ("123456789", ["123456789"]),  # Valid 9-digit phone starting with 1
            ("012345678", []),  # Invalid - starts with 0
            ("0407156596", []),  # Should NOT match - this is a rodne cislo
            ("+420 734000000 text", ["+420 734000000"]),
            ("text 602 123 456 more", ["602 123 456"]),
            ("multiple +420602111222 and 734888999", ["+420602111222", "734888999"]),
        ),
    )
    def test_phone_regex(self, text, expected_phones):
        """Test PHONE_RE pattern matches valid Czech phone numbers."""
        matches = re.findall(PHONE_RE, text)
        assert matches == expected_phones

    @pytest.mark.parametrize(
        ("text", "expected_rcs"),
        (
            ("900101/1234", ["900101/1234"]),
            ("040715/6596", ["040715/6596"]),
            ("0407156596", ["0407156596"]),  # 10 digits
            ("9001011234", ["9001011234"]),  # 10 digits
            ("900101/123", ["900101/123"]),  # 9 digits with slash
            ("900101 123", []),  # With space - not supported
            ("12345", []),  # Too short
            ("123456789012", []),  # Too long
            ("DANIEL DOLEŽAL 0407156596 text", ["0407156596"]),
            ("text 900101/1234 more text", ["900101/1234"]),
        ),
    )
    def test_rc_regex(self, text, expected_rcs):
        """Test RC_RE pattern matches valid rodne cislo formats."""
        matches = re.findall(RC_RE, text)
        assert matches == expected_rcs

    def test_no_ambiguity_between_phone_and_rc(self):
        """Test that RC and phone patterns don't interfere with each other."""
        # Line with both RC and phone (from user's example)
        text = "DANIEL DOLEŽAL 0407156596 2004-07-15 00:00:00 213 DOLNÍ LOMNÁ 203 73991 JABLUNKOV +420 734000000 a@seznam.cz"

        rc_matches = re.findall(RC_RE, text)
        phone_matches = re.findall(PHONE_RE, text)

        # RC_RE finds two RCs, but only one is valid
        assert len(rc_matches) == 2
        assert rc_matches == ["0407156596", "734000000"]
        valid_rc_matches = [rc for rc in rc_matches if is_valid_rc(rc)]
        assert len(valid_rc_matches) == 1
        assert valid_rc_matches[0] == "0407156596"

        assert len(phone_matches) == 1
        assert phone_matches[0] == "+420 734000000"


class TestParseContactLine:
    """Test parse_contact_line function."""

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_valid_line_with_all_fields(self, rc):
        """Test parsing a line with RC, email, and phone."""
        rc = new_rc_if_ignored(rc)
        line = f"{rc} jan.novak@seznam.cz 602123456"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert parsed_rc == rc
        assert email == "jan.novak@seznam.cz"
        assert phone == "602123456"
        assert errors == []

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_valid_line_different_order(self, rc):
        """Test that order doesn't matter."""
        rc = new_rc_if_ignored(rc)
        line = f"{rc} jan.novak@seznam.cz 602123456"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert parsed_rc == rc
        assert email == "jan.novak@seznam.cz"
        assert phone == "602123456"
        assert errors == []

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_valid_line_with_slash_rc(self, rc):
        """Test RC with slash separator."""
        rc = new_rc_if_ignored(rc)
        original_rc = rc
        rc = rc[:6] + "/" + rc[6:]
        line = f"{rc} test@email.cz +420 602 123 456"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert parsed_rc == original_rc  # Normalized (slash removed)
        assert email == "test@email.cz"
        assert phone == "+420602123456"  # Normalized (spaces removed)
        assert errors == []

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_valid_line_email_only(self, rc):
        """Test line with only RC and email."""
        rc = new_rc_if_ignored(rc)
        line = f"{rc} marie.nova@gmail.com"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert parsed_rc == rc
        assert email == "marie.nova@gmail.com"
        assert phone is None
        assert errors == []

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_valid_line_phone_only(self, rc):
        """Test line with only RC and phone."""
        rc = new_rc_if_ignored(rc)
        line = f"{rc} +420734000000"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert parsed_rc == rc
        assert email is None
        assert phone == "+420734000000"
        assert errors == []

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_complex_line_with_extra_text(self, rc):
        """Test parsing complex line with extra text (like from export)."""
        rc = new_rc_if_ignored(rc)
        line = f"DANIEL DOLEŽAL {rc} 2004-07-15 00:00:00 213 DOLNÍ LOMNÁ 203 73991 JABLUNKOV +420 734000000 a@seznam.cz 2025-10-03 00:00:00"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert parsed_rc == rc
        assert email == "a@seznam.cz"
        assert phone == "+420734000000"
        assert errors == []

    def test_missing_rc(self):
        """Test error when RC is missing."""
        line = "jan.novak@email.cz 602123456"
        rc, email, phone, errors = parse_contact_line(line)

        assert rc is None
        assert "chybí rodné číslo" in errors

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_missing_contact_info(self, rc):
        """Test error when both email and phone are missing."""
        rc = new_rc_if_ignored(rc)
        line = rc
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert parsed_rc == rc
        assert email is None
        assert phone is None
        assert "chybí e-mail nebo telefon" in errors

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_multiple_rcs(self, rc):
        """Test error when multiple RCs are present."""
        line = f"{rc} 0407156596 test@email.cz"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert "více než jedno rodné číslo" in errors

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_multiple_emails(self, rc):
        """Test error when multiple emails are present."""
        line = f"{rc} jan@email.cz marie@email.cz"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert "více než jeden e-mail" in errors

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_multiple_phones(self, rc):
        """Test error when multiple phones are present."""
        line = f"{rc} test@email.cz 602123456 734000000"
        parsed_rc, email, phone, errors = parse_contact_line(line)

        assert "více než jedno telefonní číslo" in errors

    def test_rc_too_short(self):
        """Test error for RC that's too short."""
        line = "1234567 test@email.cz"
        rc, email, phone, errors = parse_contact_line(line)

        assert "chybí rodné číslo" in errors

    def test_rc_too_long(self):
        """Test error for RC that's too long."""
        line = "12345678901 test@email.cz"
        rc, email, phone, errors = parse_contact_line(line)

        assert "chybí rodné číslo" in errors


class TestValidateContactImportData:
    """Test validate_contact_import_data function."""

    def test_valid_lines(self):
        """Test validation with all valid lines."""
        rc1, rc2, rc3 = sample_of_rc(3)
        rc1 = new_rc_if_ignored(rc1)
        rc2 = new_rc_if_ignored(rc2)
        rc3 = new_rc_if_ignored(rc3)
        text = f"""{rc1} jan.novak@seznam.cz 602123456
{rc2[:6] + "/" + rc2[6:]} marie.nova@gmail.com
{rc3} +420734000000"""

        valid, invalid = validate_contact_import_data(text)

        assert len(valid) == 3
        assert len(invalid) == 0

    def test_mixed_valid_invalid(self):
        """Test validation with mix of valid and invalid lines."""
        rc1, rc2, rc3 = sample_of_rc(3)
        rc1 = new_rc_if_ignored(rc1)
        rc2 = new_rc_if_ignored(rc2)
        rc3 = new_rc_if_ignored(rc3)
        text = f"""{rc1} jan.novak@seznam.cz 602123456
just-email@test.cz
{rc2} +420734000000
{rc3}
multiple@email.cz and@email.cz {rc1}"""

        valid, invalid = validate_contact_import_data(text)

        assert len(valid) == 2  # Lines 1 and 3
        assert len(invalid) == 3  # Lines 2, 4, and 5

        # Check error messages
        assert any("chybí rodné číslo" in errors for line, errors in invalid)
        assert any("chybí e-mail nebo telefon" in errors for line, errors in invalid)
        assert any("více než jeden e-mail" in errors for line, errors in invalid)

    def test_empty_lines_skipped(self):
        """Test that empty lines are silently skipped."""
        rc1, rc2 = sample_of_rc(2)
        rc1 = new_rc_if_ignored(rc1)
        rc2 = new_rc_if_ignored(rc2)
        text = f"""{rc1} test@email.cz

{rc2} +420734000000

"""

        valid, invalid = validate_contact_import_data(text)

        assert len(valid) == 2
        assert len(invalid) == 0

    def test_empty_input(self):
        """Test with completely empty input."""
        text = ""

        valid, invalid = validate_contact_import_data(text)

        assert len(valid) == 0
        assert len(invalid) == 0


class TestProcessContactImportLine:
    """Test process_contact_import_line function."""

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_process_valid_line(self, rc):
        """Test processing a valid line returns structured data."""
        rc = new_rc_if_ignored(rc)
        line = f"{rc} jan.novak@seznam.cz 602123456"
        data = process_contact_import_line(line)

        assert data["rodne_cislo"] == rc
        assert data["email"] == "jan.novak@seznam.cz"
        assert data["phone"] == "602123456"

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_process_line_with_missing_optional_fields(self, rc):
        """Test processing line with only some fields."""
        rc = new_rc_if_ignored(rc)
        line = f"{rc} test@email.cz"
        data = process_contact_import_line(line)

        assert data["rodne_cislo"] == rc
        assert data["email"] == "test@email.cz"
        assert data["phone"] is None


class TestFileConversion:
    """Test file conversion functions."""

    def test_convert_xlsx_simple(self):
        """Test converting simple XLSX file to text."""
        # Create a simple workbook
        wb = Workbook()
        ws = wb.active
        ws.append(["9001011234", "jan@email.cz", "602123456"])
        ws.append(["0407156596", "marie@email.cz", "+420734000000"])

        # Save to BytesIO
        file_obj = BytesIO()
        wb.save(file_obj)
        file_obj.seek(0)

        result = convert_xlsx_to_text(file_obj)
        lines = result.split("\n")

        assert len(lines) == 2
        assert "9001011234" in lines[0]
        assert "jan@email.cz" in lines[0]
        assert "602123456" in lines[0]
        assert "0407156596" in lines[1]

    def test_convert_xlsx_with_empty_rows(self):
        """Test that empty rows are skipped."""
        wb = Workbook()
        ws = wb.active
        ws.append(["9001011234", "jan@email.cz"])
        ws.append([None, None, None])  # Empty row
        ws.append(["0407156596", "marie@email.cz"])

        file_obj = BytesIO()
        wb.save(file_obj)
        file_obj.seek(0)

        result = convert_xlsx_to_text(file_obj)
        lines = result.split("\n")

        assert len(lines) == 2  # Empty row skipped

    def test_convert_csv_simple(self):
        """Test converting simple CSV file to text."""
        csv_content = """9001011234,jan@email.cz,602123456
0407156596,marie@email.cz,+420734000000"""
        file_obj = BytesIO(csv_content.encode("utf-8"))

        result = convert_csv_to_text(file_obj)
        lines = result.split("\n")

        assert len(lines) == 2
        assert "9001011234" in lines[0]
        assert "jan@email.cz" in lines[0]

    def test_convert_csv_with_encoding(self):
        """Test CSV conversion with different encoding."""
        # Czech text with special characters
        csv_content = "9001011234,jaroslav@email.cz,Příjmení"
        file_obj = BytesIO(csv_content.encode("cp1250"))

        result = convert_csv_to_text(file_obj, encoding="cp1250")

        assert "9001011234" in result
        assert "Příjmení" in result


class TestContactImportIntegration:
    """Integration tests for contact import views."""

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_simple_contact_import(self, user, testapp, rc):
        """Test importing a simple contact."""
        rc = new_rc_if_ignored(rc)
        login(user, testapp)

        # Navigate to import page
        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]

        # Fill in data
        form["input_data"] = f"{rc} jan.novak@seznam.cz 602123456"

        # Submit form
        res = form.submit().follow()
        assert res.status_code == 200

        # Check success message
        assert "Import kontaktů proběhl úspěšně" in res
        assert "Zpracováno: 1 řádků" in res

        # Verify note was created
        note = Note.query.get(rc)
        assert note is not None
        assert "jan.novak@seznam.cz" in note.note
        assert "602123456" in note.note

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_contact_import_duplicate_detection(self, user, testapp, rc):
        """Test that duplicate contacts are not added."""
        rc = new_rc_if_ignored(rc)
        login(user, testapp)

        delete_note_if_exists(rc)

        # Create note
        note = Note(rodne_cislo=rc, note="jan.novak@seznam.cz\n602123456")
        db.session.add(note)
        db.session.commit()

        # Try to import same contacts
        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]
        form["input_data"] = f"{rc} jan.novak@seznam.cz 602123456"
        res = form.submit().follow()
        assert res.status_code == 200

        # Check that contacts were skipped
        assert res.text.count("přeskočeno: 1") == 2

        # Verify note wasn't duplicated
        note = Note.query.get(rc)
        assert note.note.count("jan.novak@seznam.cz") == 1
        assert note.note.count("602123456") == 1

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_contact_import_with_errors(self, user, testapp, rc):
        """Test import with invalid lines shows errors."""
        rc = new_rc_if_ignored(rc)
        login(user, testapp)

        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]

        # Mix of valid and invalid lines
        form[
            "input_data"
        ] = f"""{rc} jan.novak@seznam.cz 602123456
just-email@test.cz
220222222 nonexistent@email.cz"""

        res = form.submit()

        # Should show error form
        assert "Řádky s chybami" in res
        assert "chybí rodné číslo" in res
        assert "dárce s tímto rodným číslem neexistuje" in res

        # Should show valid line
        assert "Validní řádky" in res
        assert f"{rc} jan.novak@seznam.cz 602123456" in res

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_contact_import_creates_new_note(self, user, testapp, rc):
        """Test that import creates new note if none exists."""
        rc = new_rc_if_ignored(rc)
        login(user, testapp)

        delete_note_if_exists(rc)

        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]
        form["input_data"] = f"{rc} jan.novak@seznam.cz"
        res = form.submit().follow()

        # Check statistics
        assert "Nových poznámek: 1" in res

        # Verify note was created
        note = Note.query.get(rc)
        assert note is not None
        assert note.note == "jan.novak@seznam.cz"

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_contact_import_creates_new_note_with_phone(self, user, testapp, rc):
        """Test that import creates new note if none exists."""
        rc = new_rc_if_ignored(rc)
        login(user, testapp)

        delete_note_if_exists(rc)

        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]
        form["input_data"] = f"{rc} +420734000000"
        res = form.submit().follow()

        # Check statistics
        assert "Nových poznámek: 1" in res

        # Verify note was created
        note = Note.query.get(rc)
        assert note is not None
        assert note.note == "+420734000000"

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_contact_import_appends_to_existing_note(self, user, testapp, rc):
        """Test that new contacts are appended to existing note."""
        rc = new_rc_if_ignored(rc)
        login(user, testapp)

        delete_note_if_exists(rc)

        note = Note(rodne_cislo=rc, note="Existing note text")
        db.session.add(note)
        db.session.commit()

        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]
        form["input_data"] = f"{rc} jan.novak@seznam.cz 602123456"
        res = form.submit().follow()
        assert res.status_code == 200

        # Verify contacts were appended
        note = Note.query.get(rc)
        assert "Existing note text" in note.note
        assert "jan.novak@seznam.cz" in note.note
        assert "602123456" in note.note
        # Check they're on separate lines
        lines = note.note.split("\n")
        assert len(lines) == 3

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_contact_import_empty_input(self, user, testapp, rc):
        """Test that empty input is ignored."""
        rc = new_rc_if_ignored(rc)
        login(user, testapp)

        note_before = Note.query.get(rc)

        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]
        form["input_data"] = ""
        res = form.submit()
        assert res.status_code == 200

        assert "Vstupní data s kontakty - Chybí vstupní data" in res

        note_after = Note.query.get(rc)
        assert (
            note_before.note == note_after.note if note_before else note_after is None
        )


class TestNoteModelMethods:
    """Test new methods added to Note model."""

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_get_phones_from_note(self, db, rc):
        """Test extracting phone numbers from note."""
        rc = new_rc_if_ignored(rc)
        delete_note_if_exists(rc)

        note = Note(
            rodne_cislo=rc,
            note="Kontakt: +420 602 123 456\nDalší: 734000000",
        )
        db.session.add(note)
        db.session.commit()

        phones = note.get_phones_from_note()
        assert len(phones) == 2
        assert "+420 602 123 456" in phones
        assert "734000000" in phones

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_get_all_contacts(self, db, rc):
        """Test getting all contacts from note."""
        rc = new_rc_if_ignored(rc)
        delete_note_if_exists(rc)

        note = Note(
            rodne_cislo=rc,
            note="Email: jan@email.cz\nTelefon: +420602123456\nDalší: marie@email.cz",
        )
        db.session.add(note)
        db.session.commit()

        contacts = note.get_all_contacts()
        assert "emails" in contacts
        assert "phones" in contacts
        assert len(contacts["emails"]) == 2
        assert len(contacts["phones"]) == 1
        assert "jan@email.cz" in contacts["emails"]
        assert "marie@email.cz" in contacts["emails"]
        assert "+420602123456" in contacts["phones"]


class TestFileUpload:
    """Test file upload functionality for contact imports."""

    def test_upload_txt_file(self, user, testapp):
        """Test uploading a .txt file."""
        login(user, testapp)

        res = testapp.get(url_for("batch.import_contacts"))

        # Upload file (use forms[1] - file upload form is second form)
        upload_form = res.forms[1]  # File upload form
        upload_form["contact_file"] = (
            "contacts_import_valid.txt",
            open("tests/data/contacts_import_valid.txt", "rb").read(),
        )
        res = upload_form.submit()

        # Check success message
        assert "Soubor byl úspěšně načten" in res
        assert "3 řádků" in res

        # Check that data was populated
        assert "9001011234" in res
        assert "jan.novak@seznam.cz" in res

    def test_upload_csv_file(self, user, testapp):
        """Test uploading a .csv file."""
        login(user, testapp)

        res = testapp.get(url_for("batch.import_contacts"))

        # Upload file (use forms[1] - file upload form is second form)
        upload_form = res.forms[1]
        upload_form["contact_file"] = (
            "contacts_import_valid.csv",
            open("tests/data/contacts_import_valid.csv", "rb").read(),
        )
        res = upload_form.submit()

        # Check success message
        assert "Soubor byl úspěšně načten" in res
        assert "2 řádků" in res

    def test_upload_xlsx_file(self, user, testapp):
        """Test uploading a .xlsx file."""
        login(user, testapp)

        res = testapp.get(url_for("batch.import_contacts"))

        # Upload file (use forms[1] - file upload form is second form)
        upload_form = res.forms[1]
        upload_form["contact_file"] = (
            "contacts_import_valid.xlsx",
            open("tests/data/contacts_import_valid.xlsx", "rb").read(),
        )
        res = upload_form.submit()

        # Check success message
        assert "Soubor byl úspěšně načten" in res
        assert "2 řádků" in res

    def test_upload_no_file_selected(self, user, testapp):
        """Test error when no file is selected."""
        login(user, testapp)

        res = testapp.get(url_for("batch.import_contacts"))

        # Try to submit without file (use forms[1] - file upload form is second form)
        upload_form = res.forms[1]
        res = upload_form.submit().follow()

        # Check error message (in flash message after redirect)
        assert "Nebyl vybrán žádný soubor" in res

    def test_upload_unsupported_file_type(self, user, testapp):
        """Test error when uploading unsupported file type."""
        login(user, testapp)

        res = testapp.get(url_for("batch.import_contacts"))

        # Upload unsupported file type (use forms[1] - file upload form is second form)
        upload_form = res.forms[1]
        upload_form["contact_file"] = ("test.pdf", b"fake pdf content")
        res = upload_form.submit().follow()

        # Check error message (in flash message after redirect)
        assert "Nepodporovaný formát souboru" in res

    def test_upload_corrupted_xlsx_file(self, user, testapp):
        """Test error handling for corrupted XLSX file."""
        login(user, testapp)

        res = testapp.get(url_for("batch.import_contacts"))

        # Upload corrupted file (use forms[1] - file upload form is second form)
        upload_form = res.forms[1]
        upload_form["contact_file"] = ("corrupted.xlsx", b"not a real xlsx file")
        res = upload_form.submit().follow()

        # Check error message (in flash message after redirect)
        assert "Při zpracování souboru došlo k chybě" in res

    def test_upload_no_file(self, user, testapp):
        """Test submitting contact import form without file"""
        login(user, testapp)

        # Submit form without file
        res = testapp.post(
            url_for("batch.prepare_contacts_from_file"),
        ).follow()

        assert res.status_code == 200
        assert "Nebyl vybrán žádný soubor" in res


class TestContactImportErrorFixRetry:
    """Test error correction and retry workflow."""

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_import_with_errors_then_fix_and_retry(self, user, testapp, rc, db):
        """Test full workflow: submit invalid data, see errors, fix them, retry successfully."""
        rc = new_rc_if_ignored(rc)
        login(user, testapp)

        delete_note_if_exists(rc)

        # Step 1: Submit data with errors
        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]

        # Mix of valid and invalid lines
        form[
            "input_data"
        ] = f"""{rc} jan.novak@seznam.cz 602123456
just-email@test.cz"""

        res = form.submit()

        # Step 2: Check that errors are shown
        assert "Řádky s chybami" in res
        assert "chybí rodné číslo" in res

        # Check that valid line is preserved
        assert "Validní řádky" in res
        assert f"{rc} jan.novak@seznam.cz 602123456" in res

        # Verify no data was imported yet
        note = Note.query.get(rc)
        assert note is None

        # Step 3: Fix the errors and resubmit
        form = res.forms["contactImportForm"]

        # The form should have valid_lines and invalid_lines pre-populated
        # Fix the invalid lines by adding valid data
        invalid_lines_before = form["invalid_lines"].value
        assert "just-email@test.cz" in invalid_lines_before

        # Replace invalid lines with empty string
        form["invalid_lines"] = ""

        # Submit the fixed form
        res = form.submit().follow()

        # Step 4: Check success
        assert "Import kontaktů proběhl úspěšně" in res
        assert "Zpracováno: 1 řádků" in res

        # Verify data was imported
        note = Note.query.get(rc)
        assert note is not None
        assert "jan.novak@seznam.cz" in note.note
        assert "602123456" in note.note

    def test_valid_lines_normalized_when_errors_shown(self, user, testapp):
        """Test that valid lines are cleaned up to show only RC, email, and phone."""
        login(user, testapp)

        rc = next(sample_of_rc(1))
        rc = new_rc_if_ignored(rc)

        # Submit data with extra text in valid line
        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]

        # Valid line has extra text, invalid line is missing RC
        form[
            "input_data"
        ] = f"""JOHN DOE {rc} born 1990-01-01 contact: jan.novak@seznam.cz or phone 602123456 address: somewhere
just-email@test.cz"""

        res = form.submit()

        # Check that errors are shown
        assert "Řádky s chybami" in res
        assert "chybí rodné číslo" in res

        # Check that valid line is normalized (extra text removed)
        assert "Validní řádky" in res
        form = res.forms["contactImportForm"]
        valid_lines = form["valid_lines"].value

        # Should contain only RC, email, and phone
        assert rc in valid_lines
        assert "jan.novak@seznam.cz" in valid_lines
        assert "602123456" in valid_lines

        # Should NOT contain the extra text
        assert "JOHN DOE" not in valid_lines
        assert "born 1990-01-01" not in valid_lines
        assert "somewhere" not in valid_lines


class TestContactImportAuditLog:
    """Test audit logging for contact imports."""

    def test_audit_log_created_with_correct_statistics(self, user, testapp, db):
        """Test that audit log is created with correct statistics after import."""
        from registry.donor.models import ContactImportLog

        login(user, testapp)

        rc1, rc2, rc3 = sample_of_rc(3)
        rc1 = new_rc_if_ignored(rc1)
        rc2 = new_rc_if_ignored(rc2)
        rc3 = new_rc_if_ignored(rc3)
        for rc in rc1, rc2, rc3:
            delete_note_if_exists(rc)

        # Create one existing note to test update statistics
        existing_note = Note(rodne_cislo=rc1, note="Existing text")
        db.session.add(existing_note)
        db.session.commit()

        # Get count of logs before import
        logs_before = ContactImportLog.query.count()

        # Perform import with 3 lines:
        # - rc1: existing note, add email + phone (2 contacts added)
        # - rc2: new note, add email only (1 contact added)
        # - rc3: new note, add phone only (1 contact added)
        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]
        form[
            "input_data"
        ] = f"""{rc1} jan.novak@seznam.cz 602123456
{rc2} marie.nova@gmail.com
{rc3} +420734000000"""

        res = form.submit().follow()
        assert res.status_code == 200
        assert "Import kontaktů proběhl úspěšně" in res

        # Verify a new log entry was created
        logs_after = ContactImportLog.query.count()
        assert logs_after == logs_before + 1

        # Get the latest log entry
        log = ContactImportLog.query.order_by(
            ContactImportLog.imported_at.desc()
        ).first()
        assert log is not None

        # Verify statistics
        assert log.processed_lines_count == 3
        assert log.created_notes_count == 2  # rc2 and rc3 are new
        assert log.updated_notes_count == 1  # rc1 is updated
        assert log.emails_added_count == 2  # rc1 and rc2
        assert log.phones_added_count == 2  # rc1 and rc3

        # Verify user tracking
        assert log.imported_by_user_id == user.id

        # Verify input data was saved
        assert log.input_data is not None
        assert rc1 in log.input_data
        assert "jan.novak@seznam.cz" in log.input_data

        # Verify filename is None (pasted directly)
        assert log.filename is None

        # Verify the log appears on the view page
        res = testapp.get(url_for("batch.contact_import_logs"))
        assert res.status_code == 200

        # Check that the log entry is displayed in the table
        assert str(log.id) in res
        assert user.email in res
        assert "3" in res  # processed_lines_count
        assert "2" in res  # created_notes_count or emails/phones count

    def test_audit_log_with_filename_from_file_upload(self, user, testapp, tmp_path):
        """Test that filename is recorded when file is uploaded."""
        from registry.donor.models import ContactImportLog

        login(user, testapp)

        rc1, rc2, rc3 = sample_of_rc(3)
        rc1 = new_rc_if_ignored(rc1)
        rc2 = new_rc_if_ignored(rc2)
        rc3 = new_rc_if_ignored(rc3)
        # Create temporary file with the data
        temp_file = tmp_path / "test_contacts.txt"
        temp_file.write_text(
            f"{rc1} jan.novak@seznam.cz 602123456\n{rc2} marie.nova@gmail.com\n{rc3} +420734000000"
        )

        # Upload the file
        res = testapp.get(url_for("batch.import_contacts"))
        upload_form = res.forms[1]
        upload_form["contact_file"] = (temp_file.name, temp_file.read_bytes())
        res = upload_form.submit()
        assert "Soubor byl úspěšně načten" in res

        # Submit the import
        form = res.forms["contactImportForm"]
        res = form.submit().follow()
        assert "Import kontaktů proběhl úspěšně" in res

        # Get the latest log entry
        log = ContactImportLog.query.order_by(
            ContactImportLog.imported_at.desc()
        ).first()
        assert log is not None

        # Verify filename was recorded
        assert log.filename == "test_contacts.txt"

        # Verify it appears on the view page
        res = testapp.get(url_for("batch.contact_import_logs"))
        assert "test_contacts.txt" in res

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_audit_log_with_duplicate_contacts_skipped(self, user, testapp, rc, db):
        """Test that skipped duplicates are not counted in statistics."""
        from registry.donor.models import ContactImportLog

        login(user, testapp)

        rc = new_rc_if_ignored(rc)
        delete_note_if_exists(rc)

        # Create existing note with contacts
        note = Note(rodne_cislo=rc, note="jan.novak@seznam.cz\n602123456")
        db.session.add(note)
        db.session.commit()

        # Try to import same contacts
        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]
        form["input_data"] = f"{rc} jan.novak@seznam.cz 602123456"
        res = form.submit().follow()

        # Get the latest log entry
        log = ContactImportLog.query.order_by(
            ContactImportLog.imported_at.desc()
        ).first()
        assert log is not None

        # Verify statistics show 0 additions (all skipped)
        assert log.processed_lines_count == 1
        assert log.created_notes_count == 0
        assert log.updated_notes_count == 1  # Note was "updated" but nothing changed
        assert log.emails_added_count == 0  # Duplicate, skipped
        assert log.phones_added_count == 0  # Duplicate, skipped

    @pytest.mark.parametrize("rc", sample_of_rc(2))
    def test_audit_log_view_displays_input_data_in_modal(self, user, testapp, rc):
        """Test that input data can be viewed in modal on logs page."""
        from registry.donor.models import ContactImportLog

        login(user, testapp)

        delete_note_if_exists(rc)
        rc = new_rc_if_ignored(rc)

        # Perform import
        test_input = f"{rc} test@email.cz 602123456"
        res = testapp.get(url_for("batch.import_contacts"))
        form = res.forms["contactImportForm"]
        form["input_data"] = test_input
        res = form.submit().follow()

        # Get the latest log entry
        log = ContactImportLog.query.order_by(
            ContactImportLog.imported_at.desc()
        ).first()
        assert log is not None

        # Visit logs page
        res = testapp.get(url_for("batch.contact_import_logs"))
        assert res.status_code == 200

        # Check that modal with input data exists
        assert f"dataModal{log.id}" in res
        assert test_input in res  # Input data should be in the modal

        # Check that "Zobrazit" button exists
        assert "Zobrazit" in res
