from datetime import datetime

from datatables import ColumnDT, DataTables
from flask import (
    Blueprint,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import login_required
from sqlalchemy import and_

from registry.extensions import db
from registry.list.models import DonationCenter, Medals
from registry.utils import flash_errors

from .forms import AwardMedalForm, ImportForm, RemoveMedalForm
from .models import AwardedMedals, Batch, DonorsOverview, Record

blueprint = Blueprint("donor", __name__, static_folder="../static")

# TODO: Find a better place where to store these names (db.Column custom attribute?)
COLUMN_NAMES = {
    "rodne_cislo": "Rodné číslo",
    "first_name": "Jméno",
    "last_name": "Příjmení",
    "address": "Adresa",
    "city": "Město",
    "postal_code": "PSČ",
    "kod_pojistovny": "Pojišťovna",
    "donation_count_fm": "Darování - Nemocnice FM",
    "donation_count_fm_bubenik": "Darování - Krevní centrum",
    "donation_count_trinec": "Darování - Nemocnice Třinec",
    "donation_count_manual": "Darování - Jinde",
    "donation_count_total": "Darování Celkem",
    "awarded_medal_br": "Medaile - Bronz",
    "awarded_medal_st": "Medaile - Stříbro",
    "awarded_medal_zl": "Medaile - Zlato",
    "awarded_medal_kr3": "Medaile - Kříž III",
    "awarded_medal_kr2": "Medaile - Kříž II",
    "awarded_medal_kr1": "Medaile - Kříž I",
}


@blueprint.route("/import/", methods=("GET",))
@login_required
def import_data():
    import_form = ImportForm()
    return render_template("donor/import.html", form=import_form)


@blueprint.route("/import/", methods=("POST",))
@login_required
def import_data_post():
    import_form = ImportForm(request.form)
    if import_form.validate_on_submit():
        batch = Batch(
            donation_center_id=import_form.donation_center.id,
            imported_at=datetime.now(),
        )
        db.session.add(batch)
        db.session.commit()

        for line in import_form.valid_lines_content:
            record = Record.from_list([batch.id] + line.split(";"))
            db.session.add(record)
        db.session.commit()
        # After successfull import, refresh overview table
        DonorsOverview.refresh_overview()
        flash("Import proběhl úspěšně", "success")
        return redirect(url_for("public.home"))
    else:
        flash_errors(import_form)
        return render_template("donor/import.html", form=import_form)


@blueprint.route("/overview/", methods=("GET",))
@login_required
def overview():
    return render_template("donor/overview.html", column_names=COLUMN_NAMES)


@blueprint.route("/overview/data", methods=("GET",))
@login_required
def overview_data():
    """JSON end point for JS Datatable"""
    columns = [
        ColumnDT(getattr(DonorsOverview, column_name), mData=column_name)
        for column_name in COLUMN_NAMES.keys()
    ]
    query = db.session.query().select_from(DonorsOverview)
    params = request.args.to_dict()
    row_table = DataTables(params, query, columns)
    return jsonify(row_table.output_result())


@blueprint.route("/detail/<rc>", methods=("GET",))
@login_required
def detail(rc):
    remove_medal_form = RemoveMedalForm()
    overview = DonorsOverview.query.get(rc)
    records = Record.query.filter(Record.rodne_cislo == rc).all()
    donation_centers = DonationCenter.query.all()
    awarded_medals = AwardedMedals.query.filter(AwardedMedals.rodne_cislo == rc).all()
    return render_template(
        "donor/detail.html",
        overview=overview,
        donation_centers=donation_centers,
        records=records,
        awarded_medals=awarded_medals,
        remove_medal_form=remove_medal_form,
    )


@blueprint.route("/remove_medal", methods=("POST",))
@login_required
def remove_medal():
    remove_medal_form = RemoveMedalForm()
    if remove_medal_form.validate_on_submit():
        db.session.delete(remove_medal_form.awarded_medal)
        do = DonorsOverview.query.get(remove_medal_form.rodne_cislo.data)
        slug = remove_medal_form.awarded_medal.medal.slug
        setattr(do, "awarded_medal_" + slug, False)
        db.session.commit()
        flash("Medaile byla úspěšně odebrána.", "success")
    else:
        flash("Při odebrání medaile došlo k chybě.", "danger")
    return redirect(url_for("donor.detail", rc=remove_medal_form.rodne_cislo.data))


@blueprint.route("/award_prep/<medal_slug>", methods=("GET",))
@login_required
def award_prep(medal_slug):
    medal = Medals.query.filter(Medals.slug == medal_slug).first()
    donors = DonorsOverview.query.filter(
        and_(
            DonorsOverview.donation_count_total >= medal.minimum_donations,
            getattr(DonorsOverview, "awarded_medal_" + medal_slug).is_(False),
        )
    ).all()
    award_medal_form = AwardMedalForm()
    award_medal_form.add_checkboxes([d.rodne_cislo for d in donors])
    return render_template(
        "donor/award_prep.html",
        medal=medal,
        donors=donors,
        award_medal_form=award_medal_form,
    )


@blueprint.route("/award_medal", methods=("POST",))
@login_required
def award_medal():
    award_medal_form = AwardMedalForm()
    if award_medal_form.validate_on_submit():
        # TODO: Find a way how to validate dynamic form the standard way
        medal = Medals.query.get(request.form["medal_id"])

        if medal is None:
            flash("Odeslána nevalidní data.", "danger")
            return redirect(url_for("donor.overview"))

        for rodne_cislo in request.form.getlist("rodne_cislo"):
            do = DonorsOverview.query.get(rodne_cislo)
            if do is None:
                flash("Odeslána nevalidní data.", "danger")
                return redirect(url_for("donor.award_prep", medal_slug=medal.slug))

            am = AwardedMedals(rodne_cislo=rodne_cislo, medal_id=medal.id)
            db.session.add(am)
            setattr(do, "awarded_medal_" + medal.slug, True)

        db.session.commit()
        flash("Medaile uděleny.", "success")
        return redirect(url_for("donor.award_prep", medal_slug=medal.slug))
