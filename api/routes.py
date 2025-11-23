"""Application routes."""
from flask import Blueprint, jsonify, render_template

bp = Blueprint('main', __name__)


@bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


@bp.route('/')
def index():
    """Serve the main application page."""
    return render_template('index.html')

