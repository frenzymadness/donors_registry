import csv
import os
import re
from collections import defaultdict
from datetime import datetime
from glob import glob

try:
    from dbfread import DBF
    from tqdm import tqdm
except ImportError:
    pass
from sqlalchemy.exc import IntegrityError

from registry.donor.models import AwardedMedals, Batch, DonorsOverview, Record
from registry.extensions import db
from registry.list.models import DonationCenter, Medals

dc_map = {
    "FM": "fm",
    "FM_Bubenik": "fm_bubenik",
    "Jinde": None,
    "Trinec": "trinec",
}


def load_text_backups(path):
    for filename in tqdm(glob(os.path.join(path, "nemocnice/*/bck_up/data2*.txt"))):
        # 'backup/nemocnice/FM_Bubenik/bck_up/data2016_02_11_12_08_12.txt'
        m = re.match(
            r".*nemocnice/(.*)/bck_up/data([0-9]{4})_([0-9]{2})_([0-9]{2})_([0-9]{2})_([0-9]{2})_([0-9]{2}).txt",  # noqa: E501
            filename,
        )
        if not m:
            print(filename)
            assert False, "not matching filename"

        dc_name, y, m, d, H, M, S = m.groups()  # noqa: N806
        imported_at = datetime(int(y), int(m), int(d), int(H), int(M), int(S))
        if dc_name == "Jinde":
            dc_id = None
        else:
            dc_id = (
                DonationCenter.query.filter(DonationCenter.slug == dc_map[dc_name])
                .first()
                .id
            )

        batch = Batch(donation_center_id=dc_id, imported_at=imported_at)
        db.session.add(batch)
        db.session.commit()
        load_text_file(filename, batch)


def detect_encoding(filename):
    # The order is based on outputs from enca, file and chardetect tools
    for encoding in "cp1250", "iso-8859-2", "utf-8", "ascii":
        try:
            f = open(filename, encoding=encoding)
            f.read()
            return encoding
        except Exception:
            continue
        finally:
            f.close()
    raise RuntimeError(f"Cannot detect encoding for {filename}")


def load_text_file(filename, batch):  # noqa: C901
    encoding = detect_encoding(filename)
    with open(filename, encoding=encoding) as csv_file:
        reader = csv.reader(csv_file, delimiter=";")
        for index, row in enumerate(reader):
            if not row or len(row) == 1:
                continue
            elif len(row) < 8:
                print("Line too short", filename, index, row)
                continue
            elif len(row) > 8:
                print("Line too long", filename, index, row)
                new_row = []
                for element in row:
                    if element.strip() == "" or element.strip() in new_row:
                        continue
                    new_row.append(element.strip())
                if len(new_row) > 8:
                    print("ERROR: Line still too long", filename, index, row)
                else:
                    row = new_row

            try:
                (
                    rodne_cislo,
                    first_name,
                    last_name,
                    address,
                    city,
                    postal_code,
                    kod_pojistovny,
                    donation_count,
                ) = row
            except Exception:
                print("Unpacking ERROR:", filename, index, row)
                continue

            try:
                record = Record(
                    batch_id=batch.id,
                    rodne_cislo=rodne_cislo,
                    first_name=first_name.capitalize(),
                    last_name=last_name.capitalize(),
                    address=address,
                    city=city,
                    postal_code=postal_code,
                    kod_pojistovny=kod_pojistovny,
                    donation_count=int(donation_count),
                )
            except Exception:
                print("ERROR creating Record instance", filename, index, row)
                continue
            db.session.add(record)

    db.session.commit()


def load_database(path):
    data = DBF(os.path.join(path, "cck.DBF"), load=True, encoding="iso8859-2")
    medals = Medals.query.filter(Medals.slug != "plk").all()
    csv_errors = []
    for row in tqdm(data.records):
        rodne_cislo = str(row["RC"])

        record = Record.query.filter(Record.rodne_cislo == rodne_cislo).first()
        if not record and len(rodne_cislo) < 10:
            rodne_cislo = rodne_cislo.zfill(10)
            record = Record.query.filter(Record.rodne_cislo == rodne_cislo).first()

        if record is None:
            print("Row not in DB, skipping", row)
            csv_errors.append(
                f"{rodne_cislo},není v historických záznamech ale je v databázi starého programu"
            )
            continue

        # TODO: Check numbers in Donors overview

        for medal in medals:
            if row[medal.slug.upper() + "_MED"] == "ano":
                new = AwardedMedals(rodne_cislo=record.rodne_cislo, medal_id=medal.id)
                try:
                    db.session.add(new)
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    print(
                        f"Integrty Error while adding medal id"
                        f"{medal.id} for {record.rodne_cislo}"
                    )

    return csv_errors


def check_results(path):
    data = DBF(os.path.join(path, "cck.DBF"), load=True, encoding="iso8859-2")
    errors = defaultdict(int)
    csv_errors = []
    for row in tqdm(data.records):
        rodne_cislo = str(row["RC"])
        overview = DonorsOverview.query.get(rodne_cislo)
        if not overview and len(rodne_cislo) < 10:
            rodne_cislo = rodne_cislo.zfill(10)
            overview = DonorsOverview.query.get(rodne_cislo)

        if overview is None:
            print("ERROR: RC not in overview", row)
            errors["not found"] += 1
            csv_errors.append(
                f"{rodne_cislo},není v historických záznamech ale je v databázi starého programu"
            )
            continue

        old_total = 0

        for old_name, new_name in (
            ("TRINEC", "trinec"),
            ("FM", "fm"),
            ("FM_BUBENIK", "fm_bubenik"),
            ("JINDE", "manual"),
        ):
            old_count = int(row[old_name])
            new_count = getattr(overview, "donation_count_" + new_name)
            old_total += old_count

            if old_count != new_count:
                errors[new_name] += 1
                print(
                    f"ERROR: Count from {new_name} is not the same for "
                    f"{rodne_cislo}: {old_count} vs {new_count}"
                )
                csv_errors.append(
                    f"{rodne_cislo},{new_name},pocet darovani nesedi stara: {old_count} nova: {new_count}"
                )

        if old_total != overview.donation_count_total:
            errors["total"] += 1
            print(
                f"ERROR: Total count is not the same for {rodne_cislo}: "
                f"{old_total} vs {overview.donation_count_total}"
            )

    print("ERRORS:", errors)

    return csv_errors
