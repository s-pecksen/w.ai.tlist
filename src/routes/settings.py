from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_required, current_user
from src.decorators.trial_required import trial_required
from src.utils.data_manager import DataManager
from src.repositories.user_repository import UserRepository
from werkzeug.security import generate_password_hash, check_password_hash
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)
data_manager = DataManager()
user_repo = UserRepository()

@settings_bp.route("/settings", methods=["GET", "POST"])
@trial_required
def settings():
    if request.method == 'POST':
        current_user.username = request.form.get('username')
        current_user.email = request.form.get('email')
        if request.form.get('password'):
            current_user.password = generate_password_hash(request.form.get('password'))
        try:
            user_repo.update_user(current_user)
            flash('Your settings have been updated!', 'success')
        except Exception as e:
            flash(f'Failed to update settings: {e}', 'error')
        return redirect(url_for('settings.settings'))
    return render_template('settings.html')

@settings_bp.route('/settings/download', methods=['POST'])
def download_db():
    # Export encrypted DB to a temp file
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db.enc')
    os.close(tmp_fd)
    data_manager.export_encrypted_db(tmp_path)
    return send_file(tmp_path, as_attachment=True, download_name='waitlist_encrypted.db')

@settings_bp.route('/settings/upload', methods=['POST'])
def upload_db():
    file = request.files.get('dbfile')
    if not file:
        flash('No file selected.', 'error')
        return redirect(url_for('settings.settings'))
    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.db.enc')
    file.save(tmp_path)
    os.close(tmp_fd)
    try:
        data_manager.import_encrypted_db(tmp_path)
        flash('Database imported successfully!', 'success')
    except Exception as e:
        flash(f'Failed to import database: {e}', 'error')
    finally:
        os.remove(tmp_path)
    return redirect(url_for('settings.settings')) 