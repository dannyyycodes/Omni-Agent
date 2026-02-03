"""
Simple endpoint to display a video with text overlay preview
No database required - just shows the video with fact text above it
"""

from flask import Blueprint, render_template_string, request

bp = Blueprint('simple_video', __name__)

@bp.route('/video/preview')
def video_preview():
    """
    Display a video with text overlay preview
    Query params:
    - url: video URL
    - animal: animal name
    - fact: fact text
    """
    video_url = request.args.get('url', '')
    animal = request.args.get('animal', 'Animal')
    fact = request.args.get('fact', 'Interesting fact about this animal')
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ animal }} - Video Preview</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px 20px;
            }
            .container {
                max-width: 600px;
                margin: 0 auto;
            }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
            }
            .video-card {
                background: white;
                border-radius: 20px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            .fact-bar {
                background: white;
                padding: 30px;
                text-align: center;
                border-bottom: 3px solid #667eea;
            }
            .animal-name {
                font-size: 28px;
                font-weight: bold;
                color: #000;
                margin-bottom: 15px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .fact-text {
                font-size: 18px;
                color: #333;
                line-height: 1.6;
            }
            video {
                width: 100%;
                display: block;
            }
            .info {
                background: #f8f9fa;
                padding: 20px;
                text-align: center;
                color: #666;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🐾 {{ animal }} Video</h1>
            
            <div class="video-card">
                <div class="fact-bar">
                    <div class="animal-name">{{ animal }}</div>
                    <div class="fact-text">{{ fact }}</div>
                </div>
                
                {% if video_url %}
                <video controls autoplay loop>
                    <source src="{{ video_url }}" type="video/mp4">
                    Your browser does not support the video tag.
                </video>
                {% else %}
                <div class="info">
                    <p>No video URL provided</p>
                    <p style="margin-top: 10px; font-size: 12px;">
                        Add ?url=VIDEO_URL&animal=NAME&fact=FACT to the URL
                    </p>
                </div>
                {% endif %}
                
                <div class="info">
                    <p><strong>Note:</strong> This is a preview. The final version will have the fact text overlaid directly on the video using FFmpeg.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return render_template_string(html, video_url=video_url, animal=animal, fact=fact)
