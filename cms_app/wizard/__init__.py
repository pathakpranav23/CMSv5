from flask import Blueprint

wizard = Blueprint('wizard', __name__)

from . import routes
