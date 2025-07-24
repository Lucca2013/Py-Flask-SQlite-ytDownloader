from pytubefix import YouTube
from flask import Flask, render_template, request, send_file, jsonify
import os
import re
import sqlite3
from flask import session
import hashlib
from datetime import datetime

app = Flask(__name__)

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def get_db_connection():
    conn = sqlite3.connect('downloads/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_downloads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_email TEXT NOT NULL,
            video_url TEXT NOT NULL,
            video_title TEXT NOT NULL,
            video_id TEXT NOT NULL,
            download_path TEXT NOT NULL,
            download_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_email) REFERENCES usuarios(email) ON DELETE CASCADE
        )
    ''')

    conn.commit()
    conn.close()

init_db()
app.secret_key = os.urandom(24)

@app.route("/")
def index():
    if session.get('logged_in'):
        return render_template('already_loged/index.html', email=session['email'])
    else:
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
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email e senha são obrigatórios'}), 400

    password_hash = hashlib.md5(password.encode()).hexdigest()

    try:
        conn = sqlite3.connect('downloads/database.db')
        cursor = conn.cursor()

        cursor.execute("INSERT INTO usuarios (email, password) VALUES (?, ?)", (email, password_hash))
        conn.commit()

        return jsonify({'status': 'success', 'message': 'Conta criada com sucesso'})

    except sqlite3.IntegrityError:
        return jsonify({'status': 'error', 'message': 'Email já cadastrado'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        conn.close()

@app.route("/login/loging", methods=["POST"])
def loging():
    email = request.form.get('email')
    password = request.form.get('password')

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email e senha são obrigatórios'}), 400


    try:
        conn = sqlite3.connect('downloads/database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM usuarios WHERE email = ?", (email,))
        user_data = cursor.fetchone()

        if not user_data:
            # Email não encontrado
            return jsonify({
                'status': 'error',
                'message': 'Credenciais inválidas'
            }), 401

        input_password_hash = hashlib.md5(password.encode()).hexdigest()

        if input_password_hash == user_data[0]:
            session['logged_in'] = True
            session['email'] = email

            print("Todos os usuários:")
            cursor.execute("SELECT * FROM usuarios")
            for linha in cursor.fetchall():
                print(linha)

            return jsonify({
                'status': 'success',
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Credenciais inválidas'
            }), 401

    except sqlite3.Error as db_error:
        return jsonify({
            'status': 'error',
            'message': 'Erro no banco de dados'
        }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
    finally:
        if 'conn' in locals():
            conn.close()

@app.route("/account/download", methods=['POST'])
def downloadAccount():
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'message': 'Not logged in'}), 401

    try:
        url = request.form['url']
        yt = YouTube(url, use_po_token=True)
        video = yt.streams.get_highest_resolution()

        user_folder = os.path.join(DOWNLOAD_FOLDER, hashlib.md5(session['email'].encode()).hexdigest())
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        title = re.sub(r'[^\w\-_\. ]', '', yt.title)
        filename = f"{title}.mp4"
        filepath = os.path.join(user_folder, filename)

        if os.path.exists(filepath):
            return jsonify({
                'status': 'exists',
                'filename': filename,
                'title': yt.title,
                'path': f"/download_file/{hashlib.md5(session['email'].encode()).hexdigest()}/{filename}"
            })

        video.download(output_path=user_folder, filename=filename)

        conn = get_db_connection()
        conn.execute('''
            INSERT INTO historico_downloads 
            (usuario_email, video_url, video_title, video_id, download_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (session['email'], url, yt.title, yt.video_id, filepath))
        conn.commit()
        conn.close()

        return jsonify({
            'status': 'success',
            'filename': filename,
            'title': yt.title,
            'path': f"/download_file/{hashlib.md5(session['email'].encode()).hexdigest()}/{filename}"
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route("/no-account/download", methods=['POST'])
def download():
    try:
        url = request.form['url']
        yt = YouTube(url, use_po_token=True)
        video = yt.streams.get_highest_resolution()

        user_folder = os.path.join(DOWNLOAD_FOLDER)
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        title = re.sub(r'[^\w\-_\. ]', '', yt.title)
        filename = f"{title}.mp4"
        filepath = os.path.join(user_folder, filename)

        if os.path.exists(filepath):
            return jsonify({
                'status': 'exists',
                'filename': filename,
                'title': yt.title,
                'path': f"{DOWNLOAD_FOLDER}"
            })

        video.download(output_path=user_folder, filename=filename)

        return jsonify({
            'status': 'success',
            'filename': filename,
            'title': yt.title,
            'path': f"/download_file/{hashlib.md5(session['email'].encode()).hexdigest()}/{filename}"
        })

    except Exception as e:
        return jsonify({'status': 'error', 'error': str(e)}), 500

@app.route("/logout", methods = ["POST"])
@app.route("/logout", methods = ["GET"])
def logout():
    session.clear() 
    return jsonify({'status': 'success', 'message': 'Logout realizado com sucesso'}), 200


@app.route('/download_file/<path:file_request>')
def download_file(file_request):
    try:
        if session.get('logged_in'):
            print("logged in true")
            user_hash, filename = file_request.split('/', 1)
            actual_hash = hashlib.md5(session['email'].encode()).hexdigest()
            
            if user_hash != actual_hash:
                return "Unauthorized - hash não corresponde ao usuário", 403
                
            filepath = os.path.join(DOWNLOAD_FOLDER, user_hash, filename)
        else:
            # Usuário não logado - o path é apenas "nome_do_arquivo"
            filepath = os.path.join(DOWNLOAD_FOLDER, file_request)
        
        if not os.path.exists(filepath):
            return "Arquivo não encontrado", 404
            
        return send_file(filepath, as_attachment=True)
    
    except ValueError:
        # Isso ocorre se o usuário logado tentar acessar sem o hash/
        if session.get('logged_in'):
            return "Formato inválido para usuário logado - deve ser hash/nome_do_arquivo", 400
        return "Erro no formato da requisição", 400
    except Exception as e:
        print("erro no try")
        return f"Erro no servidor: {str(e)}", 500


@app.route("/get-history")
def get_history():
    if not session.get('logged_in'):
        return jsonify({'status': 'error', 'message': 'Not logged '}), 401

    try:
        conn = get_db_connection()
        history = conn.execute('''
            SELECT video_title, video_url, download_date, download_path 
            FROM historico_downloads 
            WHERE usuario_email = ?
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
    app.run(debug=True)