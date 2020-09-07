from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from registry.extensions import db
from registry.utils import flash_errors

from .forms import ImportForm
from .models import Batch, Record

blueprint = Blueprint("donor", __name__, static_folder="../static")


@blueprint.route("/import/", methods=["GET", "POST"])
@login_required
def import_data():
    if request.method == "GET":
        import_form = ImportForm()
        return render_template("donor/import.html", form=import_form)
    elif request.method == "POST":
        import_form = ImportForm(request.form)
        if import_form.validate_on_submit():
            batch = Batch(
                donation_center=import_form.donation_center.id,
                imported_at=datetime.now(),
            )
            db.session.add(batch)
            db.session.commit()

            for line in import_form.valid_lines_content:
                record = Record.from_list([batch.id] + line.split(";"))
                db.session.add(record)
            db.session.commit()
            flash("Import proběhl úspěšně")
            return redirect(url_for("public.home"))
        else:
            flash_errors(import_form)
            return render_template("donor/import.html", form=import_form)
