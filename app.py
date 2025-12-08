from flask import Flask, render_template, request, send_file, jsonify, session, send_from_directory
import os
from dotenv import load_dotenv
import re
import sqlite3
import hashlib
from datetime import datetime
import yt_dlp
from yt_dlp.utils import DownloadError

app = Flask(__name__)

# Configurations
load_dotenv()
DOWNLOAD_FOLDER = '/tmp/downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Database configuration
def get_db_connection():
    conn = sqlite3.connect('/tmp/downloads/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS download_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            video_url TEXT NOT NULL,
            video_title TEXT NOT NULL,
            video_id TEXT NOT NULL,
            download_path TEXT NOT NULL,
            download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_email) REFERENCES users(email) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()
    
def sanitize_filename(title):
    return re.sub(r'[^\w\-_\. ]', '', title)

# that funcion is import for deployment, cause in vercel only /tmp is recordable
def get_cookies_file():
    src = os.path.join(app.root_path, "cookies.txt")
    dst = "/tmp/cookies.txt"

    if not os.path.exists(dst):
        if not os.path.exists(src):
            raise Exception("cookies.txt not found")

        with open(src, "rb") as f_src:
            with open(dst, "wb") as f_dst:
                f_dst.write(f_src.read())

    return dst


def download_video(url, user_folder=None):
    try:
        output_path = user_folder if user_folder else DOWNLOAD_FOLDER
        cookies = get_cookies_file()
        if not cookies:
            raise("COOKIES not found")

        ydl_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'format': 'best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'cookiefile': cookies,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['web'],
                    'skip': ['dash', 'hls'],  
                }
            },
            'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Accept-Language': 'en-US,en;q=0.9',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            filename = f"{sanitize_filename(info['title'])}.mp4"
            filepath = os.path.join(output_path, filename)

            if os.path.exists(filepath):
                return {
                    'status': 'exists',
                    'filename': filename,
                    'title': info['title'],
                    'video_id': info['id']
                }

            ydl.download([url])

            return {
                'status': 'success',
                'filename': filename,
                'title': info['title'],
                'video_id': info['id']
            }

    except DownloadError as e:
        return {'status': 'DownloadError', 'message': str(e)}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}




init_db()
app.secret_key = os.urandom(24)

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
        'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route("/")
def index():
    if session.get('logged_in'):
        return render_template('already_loged/index.html', email=session['email'])
    return render_template('index.html')

@app.route("/no-account")
def no_account():
    return render_template('login_false/index.html')

@app.route("/create-account")
def create_account():
    return render_template('login_true/alreadynothave/index.html')

@app.route("/login")
def login():
    return render_template('login_true/alreadyhave/index.html')

@app.route("/create-account/creating", methods=['POST'])
def create_account_database():
    conn = None
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400

    password_hash = hashlib.md5(password.encode()).hexdigest()

    try:
        conn = sqlite3.connect('downloads/database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password_hash))
        conn.commit()
        return jsonify({'status': 'success', 'message': 'Account created successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Email already registered'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route("/login/loging", methods=["POST"])
def loging():
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email and password are required'}), 400

    try:
        conn = sqlite3.connect('downloads/database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE email = ?", (email,))
        user_data = cursor.fetchone()

        if not user_data:
            return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401

        input_password_hash = hashlib.md5(password.encode()).hexdigest()

        if input_password_hash == user_data[0]:
            session['logged_in'] = True
            session['email'] = email
            return jsonify({'status': 'success'})
        return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route("/account/download", methods=['POST'])
def downloadAccount():
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    try:
        url = request.form['url']
        user_folder = os.path.join(DOWNLOAD_FOLDER, hashlib.md5(session['email'].encode()).hexdigest())
        os.makedirs(user_folder, exist_ok=True)

        result = download_video(url, user_folder)
        if result['status'] == 'error':
            return jsonify(result), 500
        elif result['status'] == 'exists':
            return jsonify({
                **result,
                'path': f"/download_file/{hashlib.md5(session['email'].encode()).hexdigest()}/{result['filename']}"
            })

        filepath = os.path.join(user_folder, result['filename'])
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO download_history 
            (user_email, video_url, video_title, video_id, download_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['email'], url, result['title'], result['video_id'], filepath))
        conn.commit()
        conn.close()

        return jsonify({
            **result,
            'path': f"/download_file/{hashlib.md5(session['email'].encode()).hexdigest()}/{result['filename']}"
        })
    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500


@app.route("/no-account/download", methods=['POST'])
def download():
    try:
        url = request.form['url']
        result = download_video(url)
        if result['status'] == 'error':
            return jsonify(result), 500
        elif result['status'] == 'exists':
            return jsonify({
                **result,
                'path': f"/download_file/{result['filename']}"
            })

        return jsonify({
            **result,
            'path': f"/download_file/{result['filename']}"
        })
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear() 
    return jsonify({'status': 'success', 'message': 'Logout successful'}), 200

@app.route('/download_file/<path:file_request>')
def download_file(file_request):
    try:
        if session.get('logged_in'):
            if '/' not in file_request:
                return "Invalid format for logged in user", 400
                
            user_hash, filename = file_request.split('/', 1)
            if hashlib.md5(session['email'].encode()).hexdigest() != user_hash:
                return "Not authorized", 403
                
            filepath = os.path.join(DOWNLOAD_FOLDER, user_hash, filename)
        else:
            filepath = os.path.join(DOWNLOAD_FOLDER, file_request)
        
        if not os.path.exists(filepath):
            return "File not found", 404
            
        return send_file(filepath, as_attachment=True)
    except Exception as e:
        return f"Server error: {str(e)}", 500

@app.route("/get-history")
def get_history():
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    try:
        conn = get_db_connection()
        history = conn.execute('''
            SELECT video_title, video_url, download_date, download_path 
            FROM download_history 
            WHERE user_email = ?
            ORDER BY download_date DESC
        ''', (session['email'],)).fetchall()
        conn.close()

        history_list = [{
            'title': item['video_title'],
            'url': item['video_url'],
            'date': item['download_date'],
            'path': f"/download_file/{hashlib.md5(session['email'].encode()).hexdigest()}/{os.path.basename(item['download_path'])}"
        } for item in history]

        return jsonify({'status': 'success', 'history': history_list})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == "__main__":
    if os.getenv('FLASK_ENV') == "developement": app.run(debug=True)