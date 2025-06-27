from pytubefix import YouTube
from flask import Flask, render_template, request, send_file, jsonify
import os
import re
import time

app = Flask(__name__)

# Configurar a pasta de downloads
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/download", methods=['POST'])
def download():
    try:
        # Recebe URL do formulário
        url = request.form['url']
        
        # Criar objeto YouTube
        yt = YouTube(url)
        
        # Obter a stream de maior resolução
        video = yt.streams.get_highest_resolution()
        
        # Preparar nome do arquivo
        title = re.sub(r'[^\w\-_\. ]', '', yt.title)
        filename = f"{title}.mp4"
        filepath = os.path.join(DOWNLOAD_FOLDER, filename)
        
        # Fazer download (isso pode levar algum tempo)
        video.download(output_path=DOWNLOAD_FOLDER, filename=filename)
        
        # Retornar informações do vídeo
        return jsonify({
            'status': 'success',
            'filename': filename,
            'title': yt.title,
            'duration': yt.length,
            'resolution': video.resolution
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/download_file/<filename>')
def download_file(filename):
    return send_file(os.path.join(DOWNLOAD_FOLDER, filename), as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)