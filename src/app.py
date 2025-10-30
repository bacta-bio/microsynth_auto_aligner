#!/usr/bin/env python3
"""
Flask web server for Microsynth Auto Aligner
"""
from flask import Flask, render_template, request, jsonify
import os
import tempfile
import zipfile
import shutil
import sys

# Add the parent directory to the Python path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.microsynth_auto_aligner import run_alignment, set_log_function

# Get the absolute path to the templates and static directories
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload size
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'  # Use persistent temp directory

# Store logs and alignment results in memory for this session
logs_buffer = []
alignment_results = []

def web_log(message: str) -> None:
    """Log function that sends messages to the web interface."""
    logs_buffer.append(message)
    print(message)  # Also print to console
    # Keep only last 100 log messages
    if len(logs_buffer) > 100:
        logs_buffer.pop(0)

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/health', methods=['GET'])
def health():
    """Simple health endpoint for load balancers."""
    return jsonify({"status": "ok"}), 200

@app.route('/healthz', methods=['GET'])
def healthz():
    """Kubernetes/Compose-friendly health endpoint alias."""
    return jsonify({"status": "ok"}), 200

@app.route('/api/logs')
def get_logs():
    """Get recent log messages"""
    return jsonify({'logs': logs_buffer})

@app.route('/api/results')
def get_results():
    """Get alignment results with Benchling links"""
    return jsonify({'results': alignment_results})

@app.route('/api/upload', methods=['POST'])
def upload_files():
    """Handle file upload and extract if needed"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    # Create a temporary directory for this upload
    upload_dir = tempfile.mkdtemp(dir=app.config['UPLOAD_FOLDER'])
    
    try:
        for file in files:
            filename = file.filename
            
            # Check if it's a zip file
            if filename.lower().endswith('.zip'):
                # Save and extract zip
                zip_path = os.path.join(upload_dir, filename)
                file.save(zip_path)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(upload_dir)
                
                os.remove(zip_path)
            else:
                # Save individual file
                file.save(os.path.join(upload_dir, filename))
        
        return jsonify({
            'success': True,
            'upload_dir': upload_dir,
            'message': f'Successfully uploaded {len(files)} file(s)'
        })
    except Exception as e:
        shutil.rmtree(upload_dir, ignore_errors=True)
        return jsonify({'error': f'Error processing upload: {str(e)}'}), 500

@app.route('/api/run', methods=['POST'])
def run_alignment_api():
    """Run the alignment process"""
    global logs_buffer, alignment_results
    logs_buffer = []  # Clear logs
    alignment_results = []  # Clear previous results
    
    data = request.json
    upload_dir = data.get('upload_dir', '')
    
    if not upload_dir:
        return jsonify({'error': 'No upload directory provided'}), 400
    
    if not os.path.exists(upload_dir):
        return jsonify({'error': 'Upload directory does not exist'}), 400
    
    try:
        # Set up custom log function
        set_log_function(web_log)
        
        # Run the alignment
        success, results = run_alignment(upload_dir)
        alignment_results = results
        
        return jsonify({
            'success': success,
            'message': 'Alignment completed successfully' if success else 'Alignment failed',
            'results_count': len(results)
        })
    finally:
        # Clean up temporary files
        if upload_dir and os.path.exists(upload_dir):
            shutil.rmtree(upload_dir, ignore_errors=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)

