from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from registry.donor.models import Batch, DonorsOverview, Record
from registry.extensions import db
from registry.utils import flash_errors

from .forms import DeleteBatchForm, ImportForm

blueprint = Blueprint("batch", __name__, static_folder="../static")


@blueprint.get("/import/")
@login_required
def import_data():
    import_form = ImportForm()
    return render_template("batch/import.html", form=import_form)


@blueprint.post("/import/")
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
    batch = Batch.query.get_or_404(id)
    records = Record.query.filter(Record.batch_id == batch.id)
    delete_batch_form = DeleteBatchForm()
    return render_template(
        "batch/batch_detail.html",
        batch=batch,
        records=records,
        delete_batch_form=delete_batch_form,
    )
