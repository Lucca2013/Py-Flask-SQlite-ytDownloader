from pytubefix import YouTube
from flask import Flask, render_template, request, send_file, jsonify
import os
import re
import sqlite3
from flask import session
import hashlib
from datetime import datetime

app = Flask(__name__)

# Configurar a pasta de downloads
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)
    
# Conexão com o banco de dados
def get_db_connection():
    conn = sqlite3.connect('downloads/database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Inicializar tabelas
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
    # Recebe os dados do formulário 
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Validação básica
    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email e senha são obrigatórios'}), 400
    
    password_hash = hashlib.md5(password.encode()).hexdigest()
    
    # Conexão com o banco de dados
    try:
        conn = sqlite3.connect('downloads/database.db')
        cursor = conn.cursor()
        
        # Tenta inserir o novo usuário
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
    # Recebe os dados do formulário
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Validação básica
    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Email e senha são obrigatórios'}), 400
    
      
    try:
        conn = sqlite3.connect('downloads/database.db')
        cursor = conn.cursor()
        
        # Consulta segura usando parâmetros para evitar SQL injection
        cursor.execute("SELECT password FROM usuarios WHERE email = ?", (email,))
        user_data = cursor.fetchone()
        
        if not user_data:
            # Email não encontrado
            return jsonify({
                'status': 'error',
                'message': 'Credenciais inválidas'
            }), 401
        
        # Calcula o hash da senha fornecida
        input_password_hash = hashlib.md5(password.encode()).hexdigest()
        
        # Verifica a senha (em produção, use hashing!)
        if input_password_hash == user_data[0]:
            # Login bem-sucedido
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
            # Senha incorreta
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
        yt = YouTube(url)
        video = yt.streams.get_highest_resolution()
        
        # Criar pasta do usuário se não existir
        user_folder = os.path.join(DOWNLOAD_FOLDER, hashlib.md5(session['email'].encode()).hexdigest())
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)
        
        # Nome do arquivo seguro
        title = re.sub(r'[^\w\-_\. ]', '', yt.title)
        filename = f"{title}.mp4"
        filepath = os.path.join(user_folder, filename)
        
        # Verificar se já existe
        if os.path.exists(filepath):
            return jsonify({
                'status': 'exists',
                'filename': filename,
                'title': yt.title,
                'path': f"/download_file/{hashlib.md5(session['email'].encode()).hexdigest()}/{filename}"
            })
        
        # Fazer download
        video.download(output_path=user_folder, filename=filename)
        
        # Registrar no histórico
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

@app.route("/logout", methods = ["POST"])
def logout():
    session.clear()  # Limpa todos os dados da sessão
    return jsonify({'status': 'success', 'message': 'Logout realizado com sucesso'}), 200


@app.route('/download_file/<path:subpath>') #subpath é o que vem depois de dowload_file
def download_file(subpath):
    try:
        #se for logado ficará: emailpessoal/video.mp4 se não, apenas video.mp4, ou seja verifica se está logado
        if '/' in subpath:
            user_hash, filename = subpath.split('/', 1)
            if session.get('logged_in'):
                # Verificar se o hash_user corresponde ao email logado
                if hashlib.md5(session['email'].encode()).hexdigest() != user_hash:
                    return "Unauthorized", 403
                filepath = os.path.join(DOWNLOAD_FOLDER, user_hash, filename)
            else:
                return "Login required", 401
        else:
            # Download não logado
            filepath = os.path.join(DOWNLOAD_FOLDER, subpath)
        
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        
        return "File not found", 404
    
    except Exception as e:
        return str(e), 500

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