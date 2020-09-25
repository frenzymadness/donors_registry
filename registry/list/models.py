from registry.extensions import db


class DonationCenter(db.Model):
    __tablename__ = "donation_center"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<DonationCenter({self.slug!r})>"


class Medals(db.Model):
    __tablename__ = "medals"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<Medals({self.slug!r})>"
