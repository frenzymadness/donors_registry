from sqlalchemy import collate

from registry.extensions import db
from registry.list.models import DonationCenter, Medals
from registry.utils import capitalize, format_postal_code, split_degrees


class Batch(db.Model):
    __tablename__ = "batches"
    id = db.Column(db.Integer, primary_key=True)
    donation_center_id = db.Column(db.ForeignKey(DonationCenter.id))
    donation_center = db.relationship("DonationCenter")
    imported_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<Batch({self.id}) from {self.imported_at}>"


class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.ForeignKey(Batch.id, ondelete="CASCADE"), nullable=False)
    batch = db.relationship("Batch")
    rodne_cislo = db.Column(db.String(10), index=True, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=False)
    postal_code = db.Column(db.String(5), nullable=False)
    kod_pojistovny = db.Column(db.String(3), nullable=False)
    donation_count = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Record({self.id}) {self.rodne_cislo} from Batch {self.batch}>"

    @classmethod
    def from_list(cls, list):
        return cls(
            batch_id=list[0],
            rodne_cislo=list[1],
            first_name=list[2],
            last_name=list[3],
            address=list[4],
            city=list[5],
            postal_code=list[6],
            kod_pojistovny=list[7],
            donation_count=list[8],
        )

    def as_original(self, donation_count=None):
        fields = [
            "rodne_cislo",
            "first_name",
            "last_name",
            "address",
            "city",
            "postal_code",
            "kod_pojistovny",
            "donation_count",
        ]
        values = [str(getattr(self, field)) for field in fields]
        if donation_count:
            values[-1] = donation_count
        line = ";".join(values)
        line += "\r\n"
        return line


class IgnoredDonors(db.Model):
    __tablename__ = "ignored_donors"
    rodne_cislo = db.Column(db.String(10), primary_key=True)
    reason = db.Column(db.String, nullable=False)
    ignored_since = db.Column(db.DateTime, nullable=False)


class AwardedMedals(db.Model):
    __tablename__ = "awarded_medals"
    rodne_cislo = db.Column(db.String(10), index=True, nullable=False)
    medal_id = db.Column(db.ForeignKey(Medals.id))
    medal = db.relationship("Medals")
    # NULL means unknown data - imported from the old system
    awarded_at = db.Column(db.DateTime, nullable=True)
    __tableargs__ = (db.PrimaryKeyConstraint(rodne_cislo, medal_id),)


class DonorsOverview(db.Model):
    __tablename__ = "donors_overview"
    rodne_cislo = db.Column(db.String(10), primary_key=True)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=False)
    postal_code = db.Column(db.String(5), nullable=False)
    kod_pojistovny = db.Column(db.String(3), nullable=False)
    donation_count_fm = db.Column(db.Integer, nullable=False)
    donation_count_fm_bubenik = db.Column(db.Integer, nullable=False)
    donation_count_trinec = db.Column(db.Integer, nullable=False)
    donation_count_mp = db.Column(db.Integer, nullable=False)
    donation_count_manual = db.Column(db.Integer, nullable=False)
    donation_count_total = db.Column(db.Integer, nullable=False)
    awarded_medal_br = db.Column(db.Boolean, nullable=False)
    awarded_medal_st = db.Column(db.Boolean, nullable=False)
    awarded_medal_zl = db.Column(db.Boolean, nullable=False)
    awarded_medal_kr3 = db.Column(db.Boolean, nullable=False)
    awarded_medal_kr2 = db.Column(db.Boolean, nullable=False)
    awarded_medal_kr1 = db.Column(db.Boolean, nullable=False)
    awarded_medal_plk = db.Column(db.Boolean, nullable=False)
    note = db.relationship(
        "Note",
        uselist=False,
        primaryjoin="foreign(DonorsOverview.rodne_cislo) == Note.rodne_cislo",
    )

    frontend_column_names = {
        "rodne_cislo": "Rodné číslo",
        "first_name": "Jméno",
        "last_name": "Příjmení",
        "address": "Adresa",
        "city": "Město",
        "postal_code": "PSČ",
        "kod_pojistovny": "Pojišťovna",
        "donations": "Darování Celkem",
        "last_award": "Ocenění",
        "note": "Pozn.",
    }

    # Fields for frontend not calculated from multiple columns
    basic_fields = [
        c
        for c in frontend_column_names.keys()
        if c not in ("donations", "last_award", "note")
    ]

    def __repr__(self):
        return f"<DonorsOverview ({self.rodne_cislo})>"

    @classmethod
    def get_filter_for_search(cls, search_str):
        conditions_all = []
        for part in search_str.split():
            conditions_all.append([])
            for column_name in cls.frontend_column_names.keys():
                if hasattr(cls, column_name):
                    if column_name == "note":
                        column = Note.note
                    else:
                        column = getattr(cls, column_name)
                    contains = getattr(column, "contains")
                    conditions_all[-1].append(contains(part, autoescape=True))
        return db.and_(*[db.or_(*conditions) for conditions in conditions_all])

    @classmethod
    def get_order_by_for_column_id(cls, column_id, direction):
        column_name = list(cls.frontend_column_names.keys())[column_id]
        if hasattr(cls, column_name):
            column = getattr(cls, column_name)
            column_with_collation = collate(column, "czech")
            return (getattr(column_with_collation, direction)(),)
        elif column_name == "donations":
            column_name = "donation_count_total"
            column = getattr(cls, column_name)
            return (getattr(column, direction)(),)
        elif column_name == "last_award":
            order_by = []
            for medal in Medals.query.order_by(Medals.id.asc()).all():
                column = getattr(cls, "awarded_medal_" + medal.slug)
                order_by.append(getattr(column, direction)())
            return order_by

    def dict_for_frontend(self):
        # All standard attributes
        donor_dict = {}
        for name in self.frontend_column_names.keys():
            donor_dict[name] = getattr(self, name, None)
            # Note is special because note column contains
            # Note object but we need to get its text which
            # is in Note.note attr.
            if donor_dict[name] is not None and name == "note":
                donor_dict[name] = donor_dict[name].note
            elif donor_dict[name] is not None and name in (
                "first_name",
                "last_name",
                "address",
                "city",
            ):
                donor_dict[name] = capitalize(donor_dict[name])

        # Highest awarded medal
        for medal in Medals.query.order_by(Medals.id.desc()).all():
            if getattr(self, "awarded_medal_" + medal.slug):
                donor_dict["last_award"] = medal.title
                break
            else:
                donor_dict["last_award"] = "Žádné"
        # Dict with all donations which we use on frontend
        # to generate tooltip
        donor_dict["donations"] = {
            dc.slug: {
                "count": getattr(self, "donation_count_" + dc.slug),
                "name": dc.title,
            }
            for dc in DonationCenter.query.all()
        }
        donor_dict["donations"]["manual"] = {
            "count": self.donation_count_manual,
            "name": "Jinde",
        }
        donor_dict["donations"]["total"] = self.donation_count_total

        # Format the donor's postal code
        donor_dict["postal_code"] = format_postal_code(self.postal_code)
        return donor_dict

    @classmethod
    def refresh_overview(cls, rodne_cislo=None):
        if rodne_cislo:
            row = cls.query.get(rodne_cislo)
            if row is not None:
                db.session.delete(row)
            record = Record.query.filter(
                Record.rodne_cislo == rodne_cislo
            ).first_or_404()
            # Thanks to the lines above, we know that it's safe to create this small
            # part of the SQL query manually. Usually it's a bad idea due to possible
            # SQL injection, but, we know that rodne_cislo is valid and exists in
            # other parts of this database so it should be fine to use it like this.
            sql_condition = "records.rodne_cislo = :rodne_cislo AND "
            params = {"rodne_cislo": record.rodne_cislo}
        else:
            cls.query.delete()
            sql_condition = ""
            params = {}
        db.session.commit()
        full_query = f"""INSERT INTO "donors_overview"
    (
        "rodne_cislo",
        "first_name",
        "last_name",
        "address",
        "city",
        "postal_code",
        "kod_pojistovny",
        "donation_count_fm",
        "donation_count_fm_bubenik",
        "donation_count_trinec",
        "donation_count_mp",
        "donation_count_manual",
        "donation_count_total",
        "awarded_medal_br",
        "awarded_medal_st",
        "awarded_medal_zl",
        "awarded_medal_kr3",
        "awarded_medal_kr2",
        "awarded_medal_kr1",
        "awarded_medal_plk"
    )
SELECT
    -- "rodne_cislo" uniquely identifies a person.
    "records"."rodne_cislo",
    -- Personal data from the person’s most recent batch
    -- or from manual overrides.
    COALESCE(
        "donors_override"."first_name",
        "records"."first_name"
    ),
    COALESCE(
        "donors_override"."last_name",
        "records"."last_name"
    ),
    COALESCE(
        "donors_override"."address",
        "records"."address"
    ),
    COALESCE(
        "donors_override"."city",
        "records"."city"
    ),
    COALESCE(
        "donors_override"."postal_code",
        "records"."postal_code"
    ),
    COALESCE(
        "donors_override"."kod_pojistovny",
        "records"."kod_pojistovny"
    ),
    -- Total donation counts for each donation center. The value in
    -- a record is incremental. Thus retrieving the one from the most
    -- recent batch that belongs to the donation center. Coalescing to
    -- 0 for cases when there is no record from the donation center.
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch_id"
                 JOIN "donation_centers"
                      ON "donation_centers"."id" = "batches"."donation_center_id"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "donation_centers"."slug" = 'fm'
            ORDER BY "batches"."imported_at" DESC,
                "records"."donation_count" DESC
            LIMIT 1
        ),
        0
     ) AS "donation_count_fm",
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch_id"
                 JOIN "donation_centers"
                      ON "donation_centers"."id" = "batches"."donation_center_id"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "donation_centers"."slug" = 'fm_bubenik'
            ORDER BY "batches"."imported_at" DESC,
                "records"."donation_count" DESC
            LIMIT 1
        ),
        0
    ) AS "donation_count_fm_bubenik",
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch_id"
                 JOIN "donation_centers"
                      ON "donation_centers"."id" = "batches"."donation_center_id"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "donation_centers"."slug" = 'trinec'
            ORDER BY "batches"."imported_at" DESC,
                "records"."donation_count" DESC
            LIMIT 1
        ),
        0
    ) AS "donation_count_trinec",
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch_id"
                 JOIN "donation_centers"
                      ON "donation_centers"."id" = "batches"."donation_center_id"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "donation_centers"."slug" = 'mp'
            ORDER BY "batches"."imported_at" DESC,
                "records"."donation_count" DESC
            LIMIT 1
        ),
        0
    ) AS "donation_count_mp",
    COALESCE(
        (
            SELECT "records"."donation_count"
            FROM "records"
                 JOIN "batches"
                      ON "batches"."id" = "records"."batch_id"
            WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                AND "batches"."donation_center_id" IS NULL
            ORDER BY "batches"."imported_at" DESC,
                "records"."donation_count" DESC
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
                        ON "batches"."id" = "records"."batch_id"
                WHERE "records"."rodne_cislo" = "recent_records"."rodne_cislo"
                    AND (
                        -- NULL values represent manual entries and
                        -- cannot be compared by =.
                        "batches"."donation_center_id" =
                            "donation_center_null"."donation_center_id"
                        OR (
                            "batches"."donation_center_id" IS NULL AND
                            "donation_center_null"."donation_center_id" IS NULL
                        )
                    )
                ORDER BY "batches"."imported_at" DESC,
                    "records"."donation_count" DESC
                LIMIT 1
            ) AS "donation_count"
            FROM (
                -- All possible donation centers including NULL
                -- for manual entries.
                SELECT "donation_centers"."id" AS "donation_center_id"
                FROM "donation_centers"
                UNION
                SELECT NULL AS "donation_centers"
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
                ON "medals"."id" = "awarded_medals"."medal_id"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'br'
    ) AS "awarded_medal_br",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal_id"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'st'
    ) AS "awarded_medal_st",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal_id"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'zl'
    ) AS "awarded_medal_zl",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal_id"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'kr3'
    ) AS "awarded_medal_kr3",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal_id"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'kr2'
    ) AS "awarded_medal_kr2",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal_id"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'kr1'
    ) AS "awarded_medal_kr1",
    EXISTS(
        SELECT 1
        FROM "awarded_medals"
            JOIN "medals"
                ON "medals"."id" = "awarded_medals"."medal_id"
        WHERE "awarded_medals"."rodne_cislo" = "records"."rodne_cislo"
            AND "medals"."slug" = 'plk'
    ) AS "awarded_medal_plk"
FROM (
    SELECT
        "rodna_cisla"."rodne_cislo",
        (
            -- Looks up the most recently imported batch for a given
            -- person, regardless of the donation center. This is used
            -- only to link the most recent personal data as the
            -- combination of "rodne_cislo" and "batch" is unique.
            SELECT "records"."id"
            FROM "records"
                JOIN "batches"
                    ON "batches"."id" = "records"."batch_id"
            WHERE "records"."rodne_cislo" = "rodna_cisla"."rodne_cislo"
            ORDER BY "batches"."imported_at" DESC,
                "records"."donation_count" DESC
            LIMIT 1
        ) AS "record_id"
    FROM (
        -- The ultimate core. We need all people, not records or
        -- batches. People are uniquely identified by their
        -- "rodne_cislo".
        SELECT DISTINCT "rodne_cislo"
        FROM "records"
        WHERE {sql_condition} "records"."rodne_cislo" NOT IN (
            SELECT "rodne_cislo" FROM "ignored_donors"
        )
    ) AS "rodna_cisla"
) AS "recent_records"
    JOIN "records"
        ON "records"."id" = "recent_records"."record_id"
    LEFT JOIN "donors_override"
        ON "donors_override"."rodne_cislo" = "records"."rodne_cislo";
"""  # nosec

        db.session.execute(full_query, params)
        db.session.commit()

        # Code moving degrees from last_name to first_name.
        if rodne_cislo:
            donors_with_degrees = (DonorsOverview.query.get(rodne_cislo),)
        else:
            # Because only 4 % of donors have a degree, it makes
            # sense to pre-select them via this query.
            donors_with_degrees = DonorsOverview.query.filter(
                db.or_(
                    DonorsOverview.last_name.contains(" "),
                    DonorsOverview.last_name.contains("."),
                    DonorsOverview.last_name.contains(","),
                )
            ).all()

        for donor in donors_with_degrees:
            last_name, degrees = split_degrees(donor.last_name)
            if degrees:
                donor.first_name = degrees + " " + donor.first_name
                donor.last_name = last_name
                db.session.add(donor)

        db.session.commit()


class Note(db.Model):
    __tablename__ = "notes"
    rodne_cislo = db.Column(db.String(10), primary_key=True)
    note = db.Column(db.Text)


class DonorsOverride(db.Model):
    __tablename__ = "donors_override"
    rodne_cislo = db.Column(db.String(10), primary_key=True)
    first_name = db.Column(db.String)
    last_name = db.Column(db.String)
    address = db.Column(db.String)
    city = db.Column(db.String)
    postal_code = db.Column(db.String(5))
    kod_pojistovny = db.Column(db.String(3))

    def to_dict(self):
        result = {}
        for field in DonorsOverview.basic_fields:
            if getattr(self, field) is not None:
                result[field] = str(getattr(self, field))
            else:
                result[field] = None

        return result
