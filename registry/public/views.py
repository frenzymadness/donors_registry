"""Public section, including homepage and signup."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from registry.extensions import login_manager
from registry.public.forms import LoginForm
from registry.user.models import User
from registry.utils import flash_errors

blueprint = Blueprint("public", __name__, static_folder="../static")


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.query.get(int(user_id))


@blueprint.route("/", methods=("GET",))
def home():
    """Home page."""
    form = LoginForm(request.form)
    return render_template("public/home.html", form=form)


@blueprint.route("/", methods=("POST",))
def home_post():
    """Home page."""
    form = LoginForm(request.form)
    if request.method == "POST":
        if form.validate_on_submit():
            login_user(form.user)
            flash("Přihlášení proběhlo úspěšně.", "success")
            redirect_url = request.args.get("next") or url_for("public.home")
            return redirect(redirect_url)
        else:
            flash_errors(form)
    return render_template("public/home.html", form=form)


@blueprint.route("/logout/")
@login_required
def logout():
    """Logout."""
    logout_user()
    flash("Odhlášení bylo úspěšné.", "info")
    return redirect(url_for("public.home"))
