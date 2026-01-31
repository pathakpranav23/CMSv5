from flask import Blueprint

super_admin = Blueprint('super_admin', __name__)

from . import routes
