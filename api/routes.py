"""Application routes."""
from flask import Blueprint, jsonify, render_template, request
import os

bp = Blueprint('main', __name__)


@bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


@bp.route('/debug/routing', methods=['GET'])
def debug_routing():
    """Debug endpoint to check routing configuration."""
    return jsonify({
        'path_info': request.environ.get('PATH_INFO', ''),
        'script_name': request.environ.get('SCRIPT_NAME', ''),
        'application_root': os.environ.get('APPLICATION_ROOT', 'NOT SET'),
        'full_path': request.full_path,
        'url': request.url,
        'base_url': request.base_url,
    }), 200


@bp.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')

