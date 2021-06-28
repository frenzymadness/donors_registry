from datetime import datetime

from flask import (
    Blueprint,
    abort,
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
    IgnoreDonorForm,
    NoteForm,
    RemoveFromIgnoredForm,
    RemoveMedalForm,
)
from .models import AwardedMedals, DonorsOverview, IgnoredDonors, Note, Record

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
    "donations": "Darování Celkem",
    "last_award": "Ocenění",
}


@blueprint.get("/overview/")
@login_required
def overview():
    return render_template("donor/overview.html", column_names=COLUMN_NAMES)


@blueprint.get("/overview/data")  # noqa: C901 FIXME
@login_required
def overview_data():
    """JSON end point for JS Datatable"""
    params = request.args.to_dict()

    # Lists and total numbers
    all_medals = Medals.query.order_by(Medals.id.desc()).all()
    all_donation_centers = DonationCenter.query.all()
    all_records_count = DonorsOverview.query.count()
    # WHERE part
    if params["search[value]"]:
        conditions_all = []
        for part in params["search[value]"].split():
            conditions_all.append([])
            for column_name in COLUMN_NAMES.keys():
                if hasattr(DonorsOverview, column_name):
                    column = getattr(DonorsOverview, column_name)
                    contains = getattr(column, "contains")
                    conditions_all[-1].append(contains(part, autoescape=True))
        filter_ = db.and_(*[db.or_(*conditions) for conditions in conditions_all])
    else:
        filter_ = True

    # ORDER BY part
    order_by_column_id = int(params["order[0][column]"])
    order_by_column_name = list(COLUMN_NAMES.keys())[order_by_column_id]
    order_by_direction = params["order[0][dir]"]
    if hasattr(DonorsOverview, order_by_column_name):
        order_by_column = getattr(DonorsOverview, order_by_column_name)
        order_by = (getattr(order_by_column, order_by_direction)(),)
    elif order_by_column_name == "donations":
        order_by_column_name = "donation_count_total"
        order_by_column = getattr(DonorsOverview, order_by_column_name)
        order_by = (getattr(order_by_column, order_by_direction)(),)
    elif order_by_column_name == "last_award":
        order_by = []
        for medal in reversed(all_medals):
            order_by_column = getattr(DonorsOverview, "awarded_medal_" + medal.slug)
            order_by.append(getattr(order_by_column, order_by_direction)())

    # LIMIT, OFFSET
    limit = int(params["length"])
    offset = int(params["start"])

    # Final query without limits to see how many records we have after filtering
    # this number is important for pagination
    filtered_records_count = (
        DonorsOverview.query.filter(filter_).order_by(*order_by).count()
    )
    # Final query
    overview = (
        DonorsOverview.query.filter(filter_)
        .order_by(*order_by)
        .limit(limit)
        .offset(offset)
        .all()
    )

    # Data processing
    final_list = []
    for donor in overview:
        # All standard attributes
        donor_dict = {name: getattr(donor, name, None) for name in COLUMN_NAMES.keys()}
        # Highest awarded medal
        for medal in all_medals:
            if getattr(donor, "awarded_medal_" + medal.slug):
                donor_dict["last_award"] = medal.title
                break
            else:
                donor_dict["last_award"] = "Žádné"
        # Dict with all donations which we use on frontend
        # to generate tooltip
        donor_dict["donations"] = {
            dc.slug: {
                "count": getattr(donor, "donation_count_" + dc.slug),
                "name": dc.title,
            }
            for dc in all_donation_centers
        }
        donor_dict["donations"]["total"] = donor.donation_count_total
        final_list.append(donor_dict)
    return jsonify(
        {
            "data": final_list,
            "recordsTotal": all_records_count,
            "recordsFiltered": filtered_records_count,
        }
    )


@blueprint.get("/detail/<rc>")
@login_required
def detail(rc):
    remove_medal_form = RemoveMedalForm()
    award_medal_form = AwardMedalForm()
    award_medal_form.add_one_rodne_cislo(rc)
    overview = DonorsOverview.query.get(rc)
    if not overview:
        if IgnoredDonors.query.get(rc):
            flash("Dárce je ignorován a proto není jeho detail k dispozici.", "danger")
            return redirect(url_for("donor.show_ignored"))
        return abort(404)
    records = Record.query.filter(Record.rodne_cislo == rc).all()
    donation_centers = DonationCenter.query.all()
    awarded_medals = AwardedMedals.query.filter(AwardedMedals.rodne_cislo == rc).all()
    awarded_medals = {medal.medal.id: medal for medal in awarded_medals}
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

            am = AwardedMedals(
                rodne_cislo=rodne_cislo, medal_id=medal.id, awarded_at=datetime.now()
            )
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


@blueprint.get("/donor/ignore")
@login_required
def show_ignored():
    ignored = IgnoredDonors.query.all()
    return render_template(
        "donor/ignore_donor.html",
        ignore_form=IgnoreDonorForm(),
        ignored=ignored,
        unignore_form=RemoveFromIgnoredForm(),
    )


@blueprint.post("/donor/ignore/add")
@login_required
def ignore_donor():
    ignore_form = IgnoreDonorForm()
    if ignore_form.validate_on_submit():
        if not IgnoredDonors.query.get(ignore_form.rodne_cislo.data):
            ignored = IgnoredDonors(
                rodne_cislo=ignore_form.rodne_cislo.data,
                reason=ignore_form.reason.data,
                ignored_since=datetime.now(),
            )
            db.session.add(ignored)
            db.session.commit()
            DonorsOverview.remove_ignored()
            flash("Dárce ignorován.", "success")
        else:
            flash("Dárce již je v seznamu ignorovaných", "danger")
    else:
        flash("Při přidávání do ignorovaných došlo k chybě", "danger")
    return redirect(url_for("donor.show_ignored"))


@blueprint.post("/donor/ignore/remove")
@login_required
def unignore_donor():
    unignore_form = RemoveFromIgnoredForm()
    if unignore_form.validate_on_submit():
        ignored_donor = IgnoredDonors.query.get(unignore_form.rodne_cislo.data)
        db.session.delete(ignored_donor)
        db.session.commit()
        DonorsOverview.refresh_overview()
        flash("Dárce již není ignorován.", "success")
    else:
        flash("Při odebírání ze seznamu ignorovaných dárců došlo k chybě", "danger")
    return redirect(url_for("donor.show_ignored"))
