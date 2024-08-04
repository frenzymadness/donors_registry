from functools import total_ordering

from sqlalchemy.sql.expression import literal

from registry.extensions import db


class DonationCenter(db.Model):
    __tablename__ = "donation_centers"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    import_increments = db.Column(
        db.Boolean, default=False, server_default=literal(False)
    )

    def __repr__(self):
        return f"<DonationCenter({self.slug!r})>"


@total_ordering
class Medals(db.Model):
    __tablename__ = "medals"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    minimum_donations = db.Column(db.Integer, nullable=False)
    title_acc = db.Column(db.String, nullable=False)
    title_instr = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<Medals({self.slug!r})>"

    def __lt__(self, other):
        return self.minimum_donations < other.minimum_donations
