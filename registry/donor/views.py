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

from .forms import (
    AwardMedalForm,
    NoteForm,
    RemoveMedalForm,
)
from .models import AwardedMedals, DonorsOverview, Note, Record

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
    "awarded_medal_plk": "Plaketa ČČK",
}


@blueprint.get("/overview/")
@login_required
def overview():
    return render_template("donor/overview.html", column_names=COLUMN_NAMES)


@blueprint.get("/overview/data")
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


@blueprint.get("/detail/<rc>")
@login_required
def detail(rc):
    remove_medal_form = RemoveMedalForm()
    award_medal_form = AwardMedalForm()
    award_medal_form.add_one_rodne_cislo(rc)
    overview = DonorsOverview.query.get_or_404(rc)
    records = Record.query.filter(Record.rodne_cislo == rc).all()
    donation_centers = DonationCenter.query.all()
    awarded_medals = AwardedMedals.query.filter(AwardedMedals.rodne_cislo == rc).all()
    awarded_medals = [medal.medal for medal in awarded_medals]
    all_medals = Medals.query.all()
    note_form = NoteForm()
    if overview.note:
        note_form.note.data = overview.note.note
    return render_template(
        "donor/detail.html",
        overview=overview,
        donation_centers=donation_centers,
        records=records,
        awarded_medals=awarded_medals,
        all_medals=all_medals,
        remove_medal_form=remove_medal_form,
        award_medal_form=award_medal_form,
        note_form=note_form,
    )


@blueprint.post("/remove_medal")
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


@blueprint.get("/award_prep/<medal_slug>")
@login_required
def award_prep(medal_slug):
    medal = Medals.query.filter(Medals.slug == medal_slug).first_or_404()
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


@blueprint.post("/award_medal")
@login_required
def award_medal():
    award_medal_form = AwardMedalForm()
    if award_medal_form.validate_on_submit():
        # TODO: Find a way how to validate dynamic form the standard way
        medal = Medals.query.get(request.form["medal_id"])

        if medal is None:
            flash("Odeslána nevalidní data.", "danger")
            return redirect(url_for("donor.overview"))

        rodna_cisla = request.form.getlist("rodne_cislo")
        for rodne_cislo in rodna_cisla:
            do = DonorsOverview.query.get(rodne_cislo)
            if do is None:
                flash("Odeslána nevalidní data.", "danger")
                return redirect(url_for("donor.award_prep", medal_slug=medal.slug))

            am = AwardedMedals(rodne_cislo=rodne_cislo, medal_id=medal.id)
            db.session.add(am)
            setattr(do, "awarded_medal_" + medal.slug, True)

        db.session.commit()
        if len(rodna_cisla) == 1:
            flash("Medaile udělena.", "success")
        else:
            flash("Medaile uděleny.", "success")
        return redirect(request.referrer)


@blueprint.post("/note/save")
@login_required
def save_note():
    note_form = NoteForm()
    note = Note.query.get(note_form.rodne_cislo.data)
    if note:
        note.note = note_form.note.data
    else:
        note = Note(rodne_cislo=note_form.rodne_cislo.data, note=note_form.note.data)
    db.session.add(note)
    db.session.commit()
    flash("Poznámka uložena.", "success")
    return redirect(url_for("donor.detail", rc=note_form.rodne_cislo.data))
