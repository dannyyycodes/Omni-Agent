"""
Diagnostic endpoint to check if video processing dependencies are working
"""

from flask import Blueprint, jsonify
import subprocess
import os

bp = Blueprint('diagnostic', __name__)

@bp.route('/api/diagnostic')
def diagnostic():
    """Check if all dependencies are available"""
    
    results = {
        'status': 'ok',
        'checks': {}
    }
    
    # Check FFmpeg
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
        results['checks']['ffmpeg'] = {
            'available': result.returncode == 0,
            'version': result.stdout.split('\n')[0] if result.returncode == 0 else None
        }
    except Exception as e:
        results['checks']['ffmpeg'] = {
            'available': False,
            'error': str(e)
        }
    
    # Check Pillow
    try:
        from PIL import Image
        results['checks']['pillow'] = {
            'available': True,
            'version': Image.__version__ if hasattr(Image, '__version__') else 'unknown'
        }
    except Exception as e:
        results['checks']['pillow'] = {
            'available': False,
            'error': str(e)
        }
    
    # Check output directory
    output_dir = os.environ.get('VIDEO_OUTPUT_DIR', '/tmp/omni_videos')
    try:
        os.makedirs(output_dir, exist_ok=True)
        results['checks']['output_dir'] = {
            'available': True,
            'path': output_dir,
            'writable': os.access(output_dir, os.W_OK)
        }
    except Exception as e:
        results['checks']['output_dir'] = {
            'available': False,
            'error': str(e)
        }
    
    # Check fonts
    font_paths = [
        '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    ]
    results['checks']['fonts'] = {}
    for font_path in font_paths:
        results['checks']['fonts'][font_path] = os.path.exists(font_path)
    
    return jsonify(results)
