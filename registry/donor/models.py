from registry.extensions import db
from registry.list.models import DonationCenter, Medals


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

    def as_original(self):
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
        line = ";".join([str(getattr(self, field)) for field in fields])
        line += "\n"
        return line


class AwardedMedals(db.Model):
    __tablename__ = "awarded_medals"
    rodne_cislo = db.Column(db.String(10), index=True, nullable=False)
    medal_id = db.Column(db.ForeignKey(Medals.id))
    medal = db.relationship("Medals")
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

    def __repr__(self):
        return f"<DonorsOverview ({self.rodne_cislo})>"

    @classmethod
    def refresh_overview(cls):
        cls.query.delete()
        db.session.execute(
            """INSERT INTO "donors_overview"
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
    ) AS "rodna_cisla"
) AS "recent_records"
    JOIN "records"
        ON "records"."id" = "recent_records"."record_id";"""
        )
        db.session.commit()


class Note(db.Model):
    __tablename__ = "notes"
    rodne_cislo = db.Column(db.String(10), primary_key=True)
    note = db.Column(db.Text)
