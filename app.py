from flask import Flask, request, jsonify
import subprocess
import os
import uuid
import base64
import shutil

app = Flask(__name__)

TEMP_DIR = '/tmp/voice-separator'
os.makedirs(TEMP_DIR, exist_ok=True)

@app.route('/separate-voice', methods=['POST'])
def separate_voice():
    """
    Separa la voce da un video/audio usando Demucs.
    
    Input JSON:
    - video: base64 del video/audio
    - input_ext: estensione input (mp4, mkv, wav, mp3) - default: mp4
    
    Output JSON:
    - vocals: base64 della traccia vocale isolata (wav)
    - success: true/false
    """
    try:
        data = request.get_json()
        
        if not data or 'video' not in data:
            return jsonify({'error': 'video base64 required', 'success': False}), 400
        
        video_b64 = data['video']
        input_ext = data.get('input_ext', 'mp4')
        
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(TEMP_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        input_file = os.path.join(job_dir, f'input.{input_ext}')
        audio_file = os.path.join(job_dir, 'audio.wav')
        output_dir = os.path.join(job_dir, 'separated')
        
        try:
            # 1. Salva il video input
            video_bytes = base64.b64decode(video_b64)
            with open(input_file, 'wb') as f:
                f.write(video_bytes)
            
            # 2. Estrai audio con FFmpeg
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-i', input_file,
                '-vn', '-acodec', 'pcm_s16le',
                '-ar', '44100', '-ac', '2',
                audio_file
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return jsonify({
                    'error': f'FFmpeg failed: {result.stderr}',
                    'success': False
                }), 500
            
            # 3. Separa con Demucs
            demucs_cmd = [
                'python', '-m', 'demucs',
                '-n', 'htdemucs',  # modello
                '-o', output_dir,
                '--two-stems', 'vocals',  # solo vocals vs resto
                audio_file
            ]
            
            result = subprocess.run(demucs_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return jsonify({
                    'error': f'Demucs failed: {result.stderr}',
                    'success': False
                }), 500
            
            # 4. Trova il file vocals (escludi no_vocals)
            vocals_file = None
            for root, dirs, files in os.walk(output_dir):
                for f in files:
                    # Cerca 'vocals' ma NON 'no_vocals'
                    if 'vocals' in f.lower() and 'no_vocals' not in f.lower():
                        vocals_file = os.path.join(root, f)
                        break
            
            if not vocals_file or not os.path.exists(vocals_file):
                return jsonify({
                    'error': 'Vocals file not found',
                    'success': False
                }), 500
            
            # 5. Leggi e converti in base64
            with open(vocals_file, 'rb') as f:
                vocals_bytes = f.read()
            vocals_b64 = base64.b64encode(vocals_bytes).decode('utf-8')
            
            return jsonify({
                'vocals': vocals_b64,
                'format': 'wav',
                'mimeType': 'audio/wav',
                'success': True
            })
            
        finally:
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
                
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'voice-separator',
        'model': 'htdemucs'
    })


@app.route('/', methods=['GET'])
def info():
    return jsonify({
        'name': 'Voice Separator API',
        'version': '1.0.0',
        'endpoints': {
            'POST /separate-voice': 'Separa voce (body: { video: base64, input_ext?: mp4|mkv|wav })',
            'GET /health': 'Health check'
        }
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
