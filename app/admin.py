from flask import Blueprint, current_app
from flask_login import login_required

admin = Blueprint('admin', __name__)

@admin.route('/clear_cache')
def clear_cache():
    current_app.cache.clear()
    return "Cache cleared", 200
