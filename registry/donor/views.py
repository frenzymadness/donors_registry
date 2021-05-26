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
from registry.utils import flash_errors

from .forms import (
    AwardMedalForm,
    DonorsOverrideForm,
    IgnoreDonorForm,
    NoteForm,
    RemoveFromIgnoredForm,
    RemoveMedalForm,
)
from .models import (
    AwardedMedals,
    DonorsOverride,
    DonorsOverview,
    IgnoredDonors,
    Note,
    Record,
)


blueprint = Blueprint("donor", __name__, static_folder="../static")


@blueprint.get("/overview/")
@login_required
def overview():
    return render_template(
        "donor/overview.html", column_names=DonorsOverview.frontend_column_names
    )


@blueprint.get("/overview/data")
@login_required
def overview_data():
    """JSON end point for JS Datatable"""
    params = request.args.to_dict()
    all_records_count = DonorsOverview.query.count()

    # WHERE part
    if params["search[value]"]:
        filter_ = DonorsOverview.get_filter_for_search(params["search[value]"])
    else:
        filter_ = True

    # ORDER BY part
    order_by = DonorsOverview.get_order_by_for_column_id(
        int(params["order[0][column]"]), params["order[0][dir]"]
    )

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
        final_list.append(donor.dict_for_frontend())
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
    donors_override_form = DonorsOverrideForm().init_fields(rc)

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
        donors_override_form=donors_override_form,
    )


@blueprint.get("/detail/<rc>/award_document/<medal_slug>/")
@login_required
def render_award_document(rc, medal_slug):
    overview = DonorsOverview.query.get_or_404(rc)
    medal = Medals.query.filter_by(slug=medal_slug).first_or_404()

    return render_template(
        "donor/award_document.html",
        overview=overview,
        medal=medal,
        today=datetime.now().strftime("%-d. %-m. %Y"),
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


@blueprint.post("/override")
@login_required
def save_override():
    override_form = DonorsOverrideForm()
    delete = True if "delete_btn" in request.form else False

    if override_form.validate_on_submit():
        if not delete:
            override = DonorsOverride(**override_form.field_data)
            db.session.add(override)
            db.session.commit()

            DonorsOverview.refresh_overview()
            flash("Výjimka uložena", "success")
        else:
            override = DonorsOverride.query.get(override_form.rodne_cislo.data)
            if override is not None:
                db.session.delete(override)
                db.session.commit()

                DonorsOverview.refresh_overview()
                flash("Výjimka smazána", "success")
            else:
                flash("Není co mazat", "warning")
    else:
        flash_errors(override_form)

    return redirect(url_for("donor.detail", rc=override_form.rodne_cislo.data))
