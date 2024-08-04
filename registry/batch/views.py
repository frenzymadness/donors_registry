from datetime import datetime
from io import StringIO

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required
from werkzeug.datastructures import Headers
from werkzeug.wrappers import Response

from registry.donor.models import Batch, DonorsOverview, Record
from registry.extensions import db
from registry.list.models import DonationCenter
from registry.utils import flash_errors, record_as_input_data

from .forms import DeleteBatchForm, ImportForm

blueprint = Blueprint("batch", __name__, static_folder="../static")


@blueprint.get("/import/")
@blueprint.get("/import/<rodne_cislo>")
@login_required
def import_data(rodne_cislo=None):
    import_form = ImportForm()
    if rodne_cislo:
        donation_center_id = request.args.get("donation_center")
        donation_center = DonationCenter.query.get(donation_center_id)
        import_form.donation_center_id.default = donation_center_id
        # Special case for manual imports - empty value in db
        if donation_center_id == "-1":
            donation_center_db_id = None
        else:
            donation_center_db_id = donation_center_id
        import_form.process()
        last_record = (
            Record.query.join(Batch)
            .filter(Record.rodne_cislo == rodne_cislo)
            .filter(Batch.donation_center_id == donation_center_db_id)
            .order_by(Batch.imported_at.desc())
            .first()
        )
        if last_record is not None and (
            donation_center_db_id is None or donation_center.import_increments
        ):
            import_form.input_data.data = record_as_input_data(
                last_record, donation_count="_POČET_", sum_with_last=True
            )
        else:
            # No last record for the given donation center
            # take the last one and start with zero.
            last_record = (
                Record.query.join(Batch)
                .filter(Record.rodne_cislo == rodne_cislo)
                .order_by(Batch.imported_at.desc())
                .first()
            )
            import_form.input_data.data = record_as_input_data(
                last_record, donation_count="_POČET_"
            )

    return render_template("batch/import.html", form=import_form)


@blueprint.post("/import/")
@login_required
def import_data_post():
    import_form = ImportForm(request.form)
    if import_form.validate_on_submit():
        batch = Batch(
            donation_center_id=import_form.donation_center_id.data
            if import_form.donation_center_id.data != "-1"
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
        if len(import_form.valid_lines_content) == 1:
            return redirect(url_for("donor.detail", rc=record.rodne_cislo))
        else:
            return redirect(url_for("donor.overview"))
    else:
        flash_errors(import_form)
        return render_template("batch/import.html", form=import_form)


@blueprint.get("/batch_list")
@login_required
def batch_list():
    batches = Batch.query.all()
    delete_batch_form = DeleteBatchForm()
    return render_template(
        "batch/batch_list.html", batches=batches, delete_batch_form=delete_batch_form
    )


@blueprint.post("/delete_batch")
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
    return redirect(url_for("batch.batch_list"))


@blueprint.get("/batch_detail/<id>")
@login_required
def batch_detail(id):
    batch = db.get_or_404(Batch, id)
    records = Record.query.filter(Record.batch_id == batch.id)
    delete_batch_form = DeleteBatchForm()
    return render_template(
        "batch/batch_detail.html",
        batch=batch,
        records=records,
        delete_batch_form=delete_batch_form,
    )


@blueprint.route("/download_batch/<id>", methods=("GET",))
@login_required
def download_batch(id):
    content = StringIO()
    for record in Record.query.filter(Record.batch_id == id):
        content.write(record_as_input_data(record))

    content.seek(0)

    headers = Headers()
    headers.set("Content-Disposition", "attachment", filename="data.txt")

    return Response(content, mimetype="text/plain", headers=headers)
