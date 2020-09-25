from registry.extensions import db
from registry.list.models import DonationCenter, Medals


class Batch(db.Model):
    __tablename__ = "batches"
    id = db.Column(db.Integer, primary_key=True)
    donation_center = db.Column(db.ForeignKey(DonationCenter.id))
    imported_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f"<Batch({self.id}) from {self.imported_at}>"


class Record(db.Model):
    __tablename__ = "records"
    id = db.Column(db.Integer, primary_key=True)
    batch = db.Column(db.ForeignKey(Batch.id), nullable=False)
    rodne_cislo = db.Column(db.String(10), index=True, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=False)
    postal_code = db.Column(db.String(5), nullable=False)
    kod_pojistovny = db.Column(db.String(3), nullable=False)
    donation_count = db.Column(db.Integer, nullable=False)

    @classmethod
    def from_list(cls, list):
        return cls(
            batch=list[0],
            rodne_cislo=list[1],
            first_name=list[2],
            last_name=list[3],
            address=list[4],
            city=list[5],
            postal_code=list[6],
            kod_pojistovny=list[7],
            donation_count=list[8],
        )


class AwardedMedals(db.Model):
    __tablename__ = "awarded_medals"
    rodne_cislo = db.Column(db.String(10), index=True, nullable=False)
    medal = db.Column(db.ForeignKey(Medals.id))
    __tableargs__ = (db.PrimaryKeyConstraint(rodne_cislo, medal),)
