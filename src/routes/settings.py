from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.decorators.trial_required import trial_required
from src.repositories.user_repository import UserRepository
from werkzeug.security import generate_password_hash, check_password_hash
import logging

logger = logging.getLogger(__name__)

settings_bp = Blueprint('settings', __name__)
user_repo = UserRepository()

@settings_bp.route("/settings", methods=["GET", "POST"])
@trial_required
def settings():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        update_data = {}
        if username:
            update_data['username'] = username
        if email:
            update_data['email'] = email
        if password:
            update_data['password'] = generate_password_hash(password)
        
        proposal_template = request.form.get('proposal_message_template')
        if proposal_template:
            update_data['proposal_message_template'] = proposal_template
        
        try:
            user_repo.update(current_user.id, update_data)
            flash('Your settings have been updated!', 'success')
        except Exception as e:
            flash(f'Failed to update settings: {e}', 'error')
        return redirect(url_for('settings.settings'))
    return render_template('settings.html') 