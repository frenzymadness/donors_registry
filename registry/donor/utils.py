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
    -- "rodne_cislo" uniquely identifies a person.
    "records"."rodne_cislo",
    -- Personal data from the person’s most recent batch.
    "records"."first_name",
    "records"."last_name",
    "records"."address",
    "records"."city",
    "records"."postal_code",
    "records"."kod_pojistovny",
    -- Total donation counts for each donation center. The value in
    -- a record is incremental. Thus retrieving the one from the most
    -- recent batch that belongs to the donation center. Coalescing to
    -- 0 for cases when there is no record from the donation center.
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch"
                 JOIN "donation_center"
                      ON "donation_center"."id" = "batches"."donation_center"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "donation_center"."slug" = 'fm'
            ORDER BY "batches"."imported_at" DESC
            LIMIT 1
        ),
        0
     ) AS "donation_count_fm",
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch"
                 JOIN "donation_center"
                      ON "donation_center"."id" = "batches"."donation_center"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "donation_center"."slug" = 'fm_bubenik'
            ORDER BY "batches"."imported_at" DESC
            LIMIT 1
        ),
        0
    ) AS "donation_count_fm_bubenik",
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch"
                 JOIN "donation_center"
                      ON "donation_center"."id" = "batches"."donation_center"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "donation_center"."slug" = 'trinec'
            ORDER BY "batches"."imported_at" DESC
            LIMIT 1
        ),
        0
    ) AS "donation_count_trinec",
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "batches"."donation_center" IS NULL
            ORDER BY "batches"."imported_at" DESC
            LIMIT 1
        ),
        0
    ) AS "donation_count_manual",
    -- The grand total of the donation counts. Sums the most recent
    -- counts from all the donation centers and the most recent manual
    -- donation count without a donation center. Not coalescing this
    -- one, because it is not possible for a person not no have any
    -- donation record at all.
    (
        -- Sum all the respective donation counts including manual
        -- entries.
        SELECT SUM("donation_count"."donation_count")
        FROM (
            SELECT (
                -- Loads the most recent donation count for the
                -- donation center.
                SELECT "records"."donation_count"
                FROM "records"
                    JOIN "batches"
                        ON "batches"."id" = "records"."batch"
                WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                    AND (
                        -- NULL values represent manual entries and
                        -- cannot be compared by =.
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
                -- All possible donation centers including NULL
                -- for manual entries.
                SELECT "donation_center"."id" AS "donation_center"
                FROM "donation_center"
                UNION
                SELECT NULL AS "donation_center"
            ) AS "donation_center_null"
            -- Removes donation centers from which the person does
            -- not have any records. This removes the need for
            -- coalescing the value to 0 before summing.
            WHERE "donation_count" IS NOT NULL
        ) AS "donation_count"
    ) AS "donation_count_total",
    -- Awarded medals checks. Just simply query whether there is a
    -- record for the given combination of "rodne_cislo" and "medal".
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'br'
    ) AS "awarded_medal_br",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'st'
    ) AS "awarded_medal_st",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'zl'
    ) AS "awarded_medal_zl",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'kr3'
    ) AS "awarded_medal_kr3",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'kr2'
    ) AS "awarded_medal_kr2",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'kr1'
    ) AS "awarded_medal_kr1"
FROM (
    SELECT
        "rodna_cisla"."rodne_cislo",
        (
            -- Looks up the most recently imported batch for a given
            -- person, regardless of the donation center. This is used
            -- only to link the most recent personal data as the
            -- combination of "rodne_cislo" and "batch" is unique.
            SELECT "records"."batch"
            FROM "records"
                 JOIN "batches"
                    ON "batches"."id" = "records"."batch"
            WHERE "records"."rodne_cislo" = "rodna_cisla"."rodne_cislo"
            ORDER BY "batches"."imported_at" DESC
            LIMIT 1
        ) AS "batch"
    FROM (
        -- The ultimate core. We need all people, not records or
        -- batches. People are uniquely identified by their
        -- "rodne_cislo". 
        SELECT DISTINCT "rodne_cislo"
        FROM "records"
    ) AS "rodna_cisla"
) AS "recent_records"
    JOIN "records"
        ON "records"."rodne_cislo" = "recent_records"."rodne_cislo"
            AND "records"."batch" = "recent_records"."batch";""")

