from flask import Flask, request, jsonify
import subprocess
import os
import uuid
import base64
import shutil

app = Flask(__name__)

# Directory temporanea per i file
TEMP_DIR = '/tmp/voice-separator'
os.makedirs(TEMP_DIR, exist_ok=True)

@app.route('/separate-voice', methods=['POST'])
def separate_voice():
    """
    Separa la voce da un video/audio.
    
    Input JSON:
    - video: base64 del video/audio
    - format: formato output (mp3, wav, ogg) - default: mp3
    - input_ext: estensione input (mp4, mkv, wav, mp3) - default: mp4
    
    Output JSON:
    - vocals: base64 della traccia vocale isolata
    - success: true/false
    """
    try:
        data = request.get_json()
        
        if not data or 'video' not in data:
            return jsonify({'error': 'video base64 required', 'success': False}), 400
        
        video_b64 = data['video']
        output_format = data.get('format', 'mp3')
        input_ext = data.get('input_ext', 'mp4')
        
        # Genera ID unico per questa richiesta
        job_id = str(uuid.uuid4())
        job_dir = os.path.join(TEMP_DIR, job_id)
        os.makedirs(job_dir, exist_ok=True)
        
        input_file = os.path.join(job_dir, f'input.{input_ext}')
        audio_raw = os.path.join(job_dir, 'audio_raw.wav')
        output_dir = os.path.join(job_dir, 'output')
        
        try:
            # 1. Salva il video input
            video_bytes = base64.b64decode(video_b64)
            with open(input_file, 'wb') as f:
                f.write(video_bytes)
            
            # 2. Estrai audio con FFmpeg
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-i', input_file,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '44100',  # 44.1kHz sample rate
                '-ac', '2',  # Stereo
                audio_raw
            ]
            
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return jsonify({
                    'error': f'FFmpeg failed: {result.stderr}',
                    'success': False
                }), 500
            
            # 3. Separa voce con audio-separator
            separator_cmd = [
                'audio-separator',
                audio_raw,
                '--model_filename', 'htdemucs_ft.yaml',  # Modello Demucs fine-tuned
                '--output_dir', output_dir,
                '--output_format', output_format
            ]
            
            result = subprocess.run(separator_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                return jsonify({
                    'error': f'Separation failed: {result.stderr}',
                    'success': False
                }), 500
            
            # 4. Trova il file vocals
            vocals_file = None
            for f in os.listdir(output_dir):
                if 'vocals' in f.lower() or 'Vocals' in f:
                    vocals_file = os.path.join(output_dir, f)
                    break
            
            if not vocals_file or not os.path.exists(vocals_file):
                return jsonify({
                    'error': 'Vocals file not found in output',
                    'success': False
                }), 500
            
            # 5. Leggi e converti in base64
            with open(vocals_file, 'rb') as f:
                vocals_bytes = f.read()
            vocals_b64 = base64.b64encode(vocals_bytes).decode('utf-8')
            
            return jsonify({
                'vocals': vocals_b64,
                'format': output_format,
                'mimeType': f'audio/{output_format}',
                'success': True
            })
            
        finally:
            # Pulizia directory temporanea
            if os.path.exists(job_dir):
                shutil.rmtree(job_dir, ignore_errors=True)
                
    except Exception as e:
        return jsonify({
            'error': str(e),
            'success': False
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'voice-separator',
        'model': 'htdemucs_ft'
    })


@app.route('/', methods=['GET'])
def info():
    """Info endpoint"""
    return jsonify({
        'name': 'Voice Separator API',
        'version': '1.0.0',
        'description': 'Isola la voce da video/audio usando AI (Demucs)',
        'endpoints': {
            'POST /separate-voice': 'Separa voce (body: { video: base64, format?: mp3|wav|ogg, input_ext?: mp4|mkv|wav })',
            'GET /health': 'Health check'
        }
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
