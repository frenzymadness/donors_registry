"""Public section, including homepage and signup."""
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import and_

from registry.donor.models import AwardedMedals, Batch, DonorsOverview, Record
from registry.extensions import db, login_manager
from registry.list.models import Medals
from registry.public.forms import LoginForm
from registry.user.models import User
from registry.utils import flash_errors

blueprint = Blueprint("public", __name__, static_folder="../static")


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return db.session.get(User, int(user_id))  # pragma: no cover


@blueprint.get("/")
@blueprint.get("/<int:status_code>")
def home(status_code=200):
    """Home page."""
    if not current_user.is_authenticated:
        form = LoginForm(request.form)
        return render_template("public/home.html", form=form), status_code
    else:
        donors = DonorsOverview.query.count()
        awarded_medals = AwardedMedals.query.count()
        batches = Batch.query.count()
        records = Record.query.count()
        medals = Medals.query.all()
        awaiting = {}
        awarded = {}
        for medal in medals:
            count = DonorsOverview.query.filter(
                and_(
                    DonorsOverview.donation_count_total >= medal.minimum_donations,
                    getattr(DonorsOverview, "awarded_medal_" + medal.slug).is_(False),
                )
            ).count()
            awaiting[medal.slug] = count
            count = DonorsOverview.query.filter(
                getattr(DonorsOverview, "awarded_medal_" + medal.slug).is_(True)
            ).count()
            awarded[medal.slug] = count
        return (
            render_template(
                "public/home.html",
                donors=donors,
                awarded_medals=awarded_medals,
                batches=batches,
                records=records,
                medals=medals,
                awaiting=awaiting,
                awarded=awarded,
            ),
            status_code,
        )


@blueprint.post("/")
def home_post():
    """Home page."""
    form = LoginForm(request.form)
    if form.validate_on_submit():
        login_user(form.user)
        session.permanent = True
        flash("Přihlášení proběhlo úspěšně.", "success")
        redirect_url = request.args.get("next") or url_for("public.home")
        return redirect(redirect_url)

    flash_errors(form)
    return render_template("public/home.html", form=form)


@blueprint.route("/logout/")
@login_required
def logout():
    """Logout."""
    logout_user()
    flash("Odhlášení bylo úspěšné.", "info")
    return redirect(url_for("public.home"))
