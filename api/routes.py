"""Application routes."""
from flask import Blueprint, jsonify, request
import os

bp = Blueprint('main', __name__)


@bp.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200


@bp.route('/debug/routing', methods=['GET'])
def debug_routing():
    """Debug endpoint to check routing configuration."""
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Debug routing endpoint called - PATH_INFO: {request.environ.get('PATH_INFO')}")
    
    return jsonify({
        'path_info': request.environ.get('PATH_INFO', ''),
        'script_name': request.environ.get('SCRIPT_NAME', ''),
        'application_root': os.environ.get('APPLICATION_ROOT', 'NOT SET'),
        'full_path': request.full_path,
        'url': request.url,
        'base_url': request.base_url,
        'request_path': request.path,
        'all_routes': [str(rule) for rule in request.app.url_map.iter_rules()],
    }), 200


@bp.route('/')
def index():
    """API server root endpoint."""
    return jsonify({
        'name': 'F1 Market API',
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'auth': '/auth/*',
            'f1': '/api/f1/*',
            'markets': '/api/markets/*'
        }
    })

