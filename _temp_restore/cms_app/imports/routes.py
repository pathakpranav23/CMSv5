from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required
from ..main.routes import role_required
from .. import db

imports_bp = Blueprint("imports", __name__)

@imports_bp.route("/admin/bulk-import", methods=["GET"])
@login_required
@role_required("admin", "principal")
def bulk_import_dashboard():
    return render_template("admin/bulk_import.html")
