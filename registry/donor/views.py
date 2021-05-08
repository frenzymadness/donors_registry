from datetime import datetime
from io import StringIO

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
from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response

from registry.extensions import db
from registry.list.models import DonationCenter, Medals
from registry.utils import flash_errors

from .forms import (
    AwardMedalForm,
    DeleteBatchForm,
    ImportForm,
    NoteForm,
    RemoveMedalForm,
)
from .models import AwardedMedals, Batch, DonorsOverview, Note, Record

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
            donation_center_id=import_form.donation_center.id
            if import_form.donation_center
            else None,
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
    note_form = NoteForm()
    if overview.note:
        note_form.note.data = overview.note.note
    return render_template(
        "donor/detail.html",
        overview=overview,
        donation_centers=donation_centers,
        records=records,
        awarded_medals=awarded_medals,
        remove_medal_form=remove_medal_form,
        note_form=note_form,
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


@blueprint.route("/note/save", methods=("POST",))
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


@blueprint.route("/batch_list", methods=("GET",))
@login_required
def batch_list():
    batches = Batch.query.all()
    delete_batch_form = DeleteBatchForm()
    return render_template(
        "donor/batch_list.html", batches=batches, delete_batch_form=delete_batch_form
    )


@blueprint.route("/delete_batch", methods=("POST",))
@login_required
def delete_batch():
    delete_batch_form = DeleteBatchForm()
    if delete_batch_form.validate_on_submit():
        records = Record.query.filter(Record.batch_id == delete_batch_form.batch.id)
        for record in records:
            db.session.delete(record)
        db.session.delete(delete_batch_form.batch)
        db.session.commit()
        DonorsOverview.refresh_overview()
        flash("Dávka smazána.", "success")
    else:
        flash("Při odebrání dávky došlo k chybě.", "danger")
    return redirect(url_for("donor.batch_list"))


@blueprint.route("/batch_detail/<id>", methods=("GET",))
@login_required
def batch_detail(id):
    batch = Batch.query.get(id)
    records = Record.query.filter(Record.batch_id == batch.id)
    delete_batch_form = DeleteBatchForm()
    return render_template(
        "donor/batch_detail.html",
        batch=batch,
        records=records,
        delete_batch_form=delete_batch_form,
    )


@blueprint.route("/download_batch/<id>", methods=("GET",))
@login_required
def download_batch(id):
    content = StringIO()
    for record in Record.query.filter(Record.batch_id == id):
        content.write(record.as_original())

    content.seek(0)

    headers = Headers()
    headers.set("Content-Disposition", "attachment", filename="data.txt")

    return Response(content, mimetype="text/plain", headers=headers)
