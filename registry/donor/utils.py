from registry.extensions import db

from .models import DonorsOverview


def get_part_of_line(line, delimiter=";"):
    try:
        del_index = line.index(delimiter)
        return line[:del_index], line[del_index + 1 :]
    except ValueError:
        return line, ""


def is_line_valid(line):
    parts = line.split(";")
    if not parts[-1]:
        # If the last part of the line is empty we can skip the line entirely.
        # Line ending  with semicolon means that the donor has 0 dotations.
        return None

    if len(parts) == 8 and all(parts):
        return True
    else:
        return False


def repair_two_semicolons(line):
    repaired_line = line
    while ";;" in repaired_line:
        repaired_line = repaired_line.replace(";;", ";")
    return repaired_line


def repair_line_part_by_part(line):
    errors = []
    rodne_cislo, rest = get_part_of_line(line)
    if not rodne_cislo:
        errors.append("chybí rodné číslo")
    elif not rodne_cislo.isnumeric():
        errors.append("rodné číslo není číselné")

    first_name, rest = get_part_of_line(rest)
    if not first_name:
        errors.append("chybí jméno")

    last_name, rest = get_part_of_line(rest)
    if not last_name:
        errors.append("chybí příjmení")

    address, rest = get_part_of_line(rest)
    if not address:
        errors.append("chybí ulice")

    city, rest = get_part_of_line(rest)
    if not city:
        errors.append("chybí město")

    postal_code, rest = get_part_of_line(rest)
    if not postal_code:
        postal_code = "00000"
        errors.append("chybí PSČ, nahrazeno nulami")

    kod_pojistovny, rest = get_part_of_line(rest)
    if not kod_pojistovny:
        kod_pojistovny = "000"
        errors.append("chybí pojišťovna, nahrazena nulami")

    donation_count, rest = get_part_of_line(rest)
    if not donation_count or not donation_count.isnumeric():
        errors.append("počet odběrů není číselný")

    repaired_line = ";".join(
        [
            rodne_cislo,
            first_name,
            last_name,
            address,
            city,
            postal_code,
            kod_pojistovny,
            donation_count,
        ]
    )

    return repaired_line, errors


def validate_import_data(text_input):
    valid_lines = []  # List of valid lines (strings)
    invalid_lines = []  # List of tuples (line, list of comments)
    for line in text_input.splitlines():
        if is_line_valid(line):
            valid_lines.append(line)
            continue
        elif is_line_valid(line) is None:
            # None means we should skip the line because the donations count
            # is not present at the end of the line
            continue

        if ";;" in line:
            repaired_line = repair_two_semicolons(line)
            if is_line_valid(repaired_line):
                invalid_lines.append(
                    (repaired_line, ["řádek obsahoval dvojici středníků"])
                )
                continue

        repaired_line, errors = repair_line_part_by_part(line)
        invalid_lines.append((repaired_line, errors))

    return valid_lines, invalid_lines


def refresh_overview():
    DonorsOverview.query.delete()
    db.session.execute("""INSERT INTO "donors_overview"
SELECT
    "records"."rodne_cislo",
    "records"."first_name",
    "records"."last_name",
    "records"."address",
    "records"."city",
    "records"."postal_code",
    "records"."kod_pojistovny",
    COALESCE(
        (
            SELECT "_r"."donation_count"
            FROM "records" AS "_r"
                JOIN "batches" AS "_b"
                    ON "_r"."batch" = "_b"."id"
                JOIN "donation_center" AS "_dc"
                    ON "_b"."donation_center" = "_dc"."id"
            WHERE "_r"."rodne_cislo" = "records"."rodne_cislo"
                AND "_b"."id" = "records"."batch"
                AND "_dc"."slug" = 'fm'
        ),
        0
     ) AS "donation_count_fm",
    COALESCE(
        (
            SELECT COALESCE("_r"."donation_count", 0)
            FROM "records" AS "_r"
                JOIN "batches" AS "_b"
                    ON "_r"."batch" = "_b"."id"
                JOIN "donation_center" AS "_dc"
                    ON "_b"."donation_center" = "_dc"."id"
            WHERE "_r"."rodne_cislo" = "records"."rodne_cislo"
                AND "_b"."id" = "records"."batch"
                AND "_dc"."slug" = 'fm_bubenik'
        ),
        0
    ) AS "donation_count_fm_bubenik",
    COALESCE(
        (
            SELECT COALESCE("_r"."donation_count", 0)
            FROM "records" AS "_r"
                JOIN "batches" AS "_b"
                    ON "_r"."batch" = "_b"."id"
                JOIN "donation_center" AS "_dc"
                    ON "_b"."donation_center" = "_dc"."id"
            WHERE "_r"."rodne_cislo" = "records"."rodne_cislo"
                AND "_b"."id" = "records"."batch"
                AND "_dc"."slug" = 'trinec'
        ),
        0
    ) AS "donation_count_trinec",
    COALESCE(
        (
            SELECT COALESCE("_r"."donation_count", 0)
            FROM "records" AS "_r"
                JOIN "batches" AS "_b"
                    ON "_r"."batch" = "_b"."id"
                JOIN "donation_center" AS "_dc"
                    ON "_b"."donation_center" = "_dc"."id"
            WHERE "_r"."rodne_cislo" = "records"."rodne_cislo"
                AND "_b"."id" = "records"."batch"
                AND "_b"."donation_center" IS NULL
        ),
        0
    ) AS "donation_count_manual",
    COALESCE(
        (
            SELECT SUM("donation_count"."donation_count")
            FROM (
                SELECT (
                    SELECT "records"."donation_count"
                    FROM "records"
                        JOIN "batches"
                            ON "batches"."id" = "records"."batch"
                    WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                        AND (
                            "batches"."donation_center" =
                                "donation_center_null"."donation_center"
                            OR (
                                "batches"."donation_center" IS NULL AND
                                "donation_center_null"."donation_center" IS NULL
                            )
                        )
                    ORDER BY "batches"."imported_at" DESC
                    LIMIT 1
                ) AS "donation_count"
                FROM (
                    SELECT "donation_center"."id" AS "donation_center"
                    FROM "donation_center"
                    UNION
                    SELECT NULL AS "donation_center"
                ) AS "donation_center_null"
             WHERE "donation_count" IS NOT NULL
            ) AS "donation_count"
        ),
        0
    ) AS "donation_count_total",
    EXISTS(
        SELECT 1
        FROM "awarded_medals" AS "_am"
            JOIN "medals" AS "_m"
                ON "_m"."id" = "_am"."medal"
        WHERE "_am"."rodne_cislo" = "records"."rodne_cislo"
            AND "_m"."slug" = 'br'
    ) AS "awarded_medal_br",
    EXISTS(
        SELECT 1
        FROM "awarded_medals" AS "_am"
            JOIN "medals" AS "_m"
                ON "_m"."id" = "_am"."medal"
        WHERE "_am"."rodne_cislo" = "records"."rodne_cislo"
            AND "_m"."slug" = 'st'
    ) AS "awarded_medal_st",
    EXISTS(
        SELECT 1
        FROM "awarded_medals" AS "_am"
            JOIN "medals" AS "_m"
                ON "_m"."id" = "_am"."medal"
        WHERE "_am"."rodne_cislo" = "records"."rodne_cislo"
            AND "_m"."slug" = 'zl'
    ) AS "awarded_medal_zl",
    EXISTS(
        SELECT 1
        FROM "awarded_medals" AS "_am"
            JOIN "medals" AS "_m"
                ON "_m"."id" = "_am"."medal"
        WHERE "_am"."rodne_cislo" = "records"."rodne_cislo"
            AND "_m"."slug" = 'kr3'
    ) AS "awarded_medal_kr3",
    EXISTS(
        SELECT 1
        FROM "awarded_medals" AS "_am"
            JOIN "medals" AS "_m"
                ON "_m"."id" = "_am"."medal"
        WHERE "_am"."rodne_cislo" = "records"."rodne_cislo"
            AND "_m"."slug" = 'kr2'
    ) AS "awarded_medal_kr2",
    EXISTS(
        SELECT 1
        FROM "awarded_medals" AS "_am"
            JOIN "medals" AS "_m"
                ON "_m"."id" = "_am"."medal"
        WHERE "_am"."rodne_cislo" = "records"."rodne_cislo"
            AND "_m"."slug" = 'kr1'
    ) AS "awarded_medal_kr1"
FROM (
    SELECT
       "rodna_cisla"."rodne_cislo",
        (
            SELECT "records"."batch"
            FROM "records"
                 JOIN "batches"
                    ON "batches"."id" = "records"."batch"
            WHERE "records"."rodne_cislo" = "rodna_cisla"."rodne_cislo"
            ORDER BY "batches"."imported_at" DESC
            LIMIT 1
        ) AS "batch"
    FROM (
        SELECT DISTINCT "rodne_cislo"
        FROM "records"
    ) AS "rodna_cisla"
) AS "recent_records"
    JOIN "batches"
        ON "batches"."id" = "recent_records"."batch"
    JOIN "records"
        ON "records"."rodne_cislo" = "recent_records"."rodne_cislo"
            AND "records"."batch" = "batches"."id";""")
