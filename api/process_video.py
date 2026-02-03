"""
Process video with FFmpeg to add text overlay and create final branded output
This creates the actual final video file, not just a preview
"""

from flask import Blueprint, send_file, jsonify, request
import os
import tempfile
import requests
from utils.video_composer import VideoComposer

bp = Blueprint('process_video', __name__)

@bp.route('/api/process-video', methods=['POST'])
def process_video():
    """
    Process a video with FFmpeg to add text overlay
    
    POST body:
    {
        "video_url": "https://...",
        "animal": "Octopus",
        "fact": "Did you know..."
    }
    
    Returns: The processed video file
    """
    try:
        data = request.json
        video_url = data.get('video_url')
        animal = data.get('animal', 'Animal')
        fact = data.get('fact', 'Interesting fact')
        
        if not video_url:
            return jsonify({'error': 'video_url required'}), 400
        
        print(f"🎬 Processing video for {animal}...")
        
        # Use VideoComposer to add text overlay
        composer = VideoComposer()
        output_path = composer.add_fact_overlay(
            video_url=video_url,
            fact_text=fact,
            title=animal
        )
        
        print(f"✅ Video processed: {output_path}")
        
        # Return the processed video file
        if os.path.exists(output_path):
            return send_file(
                output_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=f"{animal.lower().replace(' ', '_')}_final.mp4"
            )
        else:
            return jsonify({'error': 'Video processing failed'}), 500
            
    except Exception as e:
        print(f"❌ Error processing video: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@bp.route('/video/final/<animal>')
def view_final_video(animal):
    """
    View the final processed video with text overlay
    Query params:
    - url: video URL
    - fact: fact text
    """
    from flask import render_template_string
    
    video_url = request.args.get('url', '')
    fact = request.args.get('fact', 'Interesting fact about this animal')
    
    # Build the process URL
    process_url = f"/api/process-video"
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>{{ animal }} - Final Video</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 40px 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
            }
            h1 {
                color: white;
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
            }
            .card {
                background: white;
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                text-align: center;
            }
            .status {
                font-size: 18px;
                color: #666;
                margin: 20px 0;
            }
            .loading {
                display: inline-block;
                width: 50px;
                height: 50px;
                border: 5px solid #f3f3f3;
                border-top: 5px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 20px 0;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 15px 30px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                margin: 10px;
                text-decoration: none;
                display: inline-block;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            }
            #videoContainer {
                margin-top: 30px;
                display: none;
            }
            video {
                width: 100%;
                max-width: 600px;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }
            .info {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
                text-align: left;
            }
            .info h3 {
                color: #667eea;
                margin-bottom: 10px;
            }
            .info p {
                color: #666;
                line-height: 1.6;
                margin: 5px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎬 {{ animal }} - Final Video</h1>
            
            <div class="card">
                <div id="processingStatus">
                    <div class="loading"></div>
                    <p class="status">Processing video with FFmpeg...</p>
                    <p style="color: #999; font-size: 14px;">Adding text overlay to create final branded video</p>
                </div>
                
                <div id="videoContainer">
                    <h2 style="margin-bottom: 20px;">✅ Final Video Ready!</h2>
                    <video id="finalVideo" controls autoplay>
                        <source src="" type="video/mp4">
                    </video>
                    <div style="margin-top: 20px;">
                        <a id="downloadBtn" class="btn" download>📥 Download Final Video</a>
                    </div>
                </div>
                
                <div class="info">
                    <h3>📋 Video Details</h3>
                    <p><strong>Animal:</strong> {{ animal }}</p>
                    <p><strong>Fact:</strong> {{ fact }}</p>
                    <p><strong>Format:</strong> 1080x1920 (9:16 for TikTok/Instagram)</p>
                    <p><strong>Text Overlay:</strong> White bar at top with animal name + fact</p>
                    <p><strong>Ready for:</strong> Social media posting</p>
                </div>
            </div>
        </div>
        
        <script>
            // Process the video on page load
            async function processVideo() {
                try {
                    const response = await fetch('/api/process-video', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            video_url: '{{ video_url }}',
                            animal: '{{ animal }}',
                            fact: '{{ fact }}'
                        })
                    });
                    
                    if (response.ok) {
                        const blob = await response.blob();
                        const url = URL.createObjectURL(blob);
                        
                        // Show the video
                        document.getElementById('processingStatus').style.display = 'none';
                        document.getElementById('videoContainer').style.display = 'block';
                        document.getElementById('finalVideo').src = url;
                        document.getElementById('downloadBtn').href = url;
                    } else {
                        document.getElementById('processingStatus').innerHTML = 
                            '<p style="color: red;">❌ Processing failed. Please try again.</p>';
                    }
                } catch (error) {
                    console.error('Error:', error);
                    document.getElementById('processingStatus').innerHTML = 
                        '<p style="color: red;">❌ Error: ' + error.message + '</p>';
                }
            }
            
            // Start processing when page loads
            processVideo();
        </script>
    </body>
    </html>
    """
    
    return render_template_string(html, animal=animal, video_url=video_url, fact=fact)
