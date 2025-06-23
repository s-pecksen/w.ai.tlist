from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from src.repositories.provider_repository import ProviderRepository
import logging

logger = logging.getLogger(__name__)

providers_bp = Blueprint('providers', __name__)
provider_repo = ProviderRepository()

@providers_bp.route("/providers", methods=["GET"])
@login_required
def list_providers():
    """Display providers management page."""
    providers = provider_repo.get_providers(current_user.id)
    return render_template("providers.html", providers=providers)

@providers_bp.route("/add_provider", methods=["POST"])
@login_required
def add_provider():
    """Add a new provider."""
    first_name = request.form.get("first_name", "").strip()
    last_initial = request.form.get("last_initial", "").strip()

    if not first_name:
        flash("First name is required", "warning")
        return redirect(url_for("providers.list_providers"))

    try:
        provider_data = {
            "user_id": current_user.id,
            "first_name": first_name,
            "last_initial": last_initial
        }
        
        result = provider_repo.create(provider_data)
        if result:
            flash("Provider added successfully", "success")
        else:
            flash("Error adding provider", "danger")
            
    except Exception as e:
        logger.error(f"Error adding provider: {e}")
        flash("An error occurred while adding the provider", "danger")

    return redirect(url_for("providers.list_providers"))

@providers_bp.route("/remove_provider", methods=["POST"])
@login_required
def remove_provider():
    """Remove a provider."""
    provider_id = request.form.get("provider_id")
    
    if not provider_id:
        flash("Provider ID is required", "warning")
        return redirect(url_for("providers.list_providers"))

    try:
        success = provider_repo.delete(provider_id, current_user.id)
        if success:
            flash("Provider removed successfully", "success")
        else:
            flash("Error removing provider", "danger")
            
    except Exception as e:
        logger.error(f"Error removing provider: {e}")
        flash("An error occurred while removing the provider", "danger")

    return redirect(url_for("providers.list_providers")) 