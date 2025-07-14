from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from src.utils.data_manager import DataManager
import os
import tempfile

settings_bp = Blueprint('settings', __name__)
data_manager = DataManager()

@settings_bp.route('/settings', methods=['GET'])
def settings():
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