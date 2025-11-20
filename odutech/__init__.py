from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
import os
import sys

app = Flask(__name__)

# =========================
# Configurações base
# =========================
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '5563bafbd7bald301ca61fc591227446')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# =========================
# Banco de Dados
# =========================
# Railway → DATABASE_URL = sqlite:////data/comunidade.db
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///comunidade.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL

# Garante que o diretório do arquivo SQLite exista
if DB_URL.startswith('sqlite:///'):
    db_path = DB_URL.replace('sqlite:///', '', 1)
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.root_path, db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    print(f"[init] Usando banco SQLite em: {db_path}")

# =========================
# Uploads (sempre em static/uploads)
# =========================
# Vamos simplificar: todos os uploads vão pra pasta dentro de /static/uploads.
# Isso funciona igual local e no Railway, e é exatamente de onde o Flask serve
# arquivos estáticos com url_for('static', ...).

static_dir = os.path.join(app.root_path, 'static')
os.makedirs(static_dir, exist_ok=True)

BASE_UPLOADS = os.path.join(static_dir, 'uploads')
os.makedirs(BASE_UPLOADS, exist_ok=True)

app.config['UPLOADS_ROOT'] = BASE_UPLOADS
app.config['UPLOAD_PHOTOS_FOLDER'] = os.path.join(BASE_UPLOADS, 'fotos')
app.config['UPLOAD_DOCS_FOLDER'] = os.path.join(BASE_UPLOADS, 'docs')

for p in (app.config['UPLOAD_PHOTOS_FOLDER'], app.config['UPLOAD_DOCS_FOLDER']):
    os.makedirs(p, exist_ok=True)

app.config.setdefault('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)

# =========================
# Extensões Flask
# =========================
database = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
csrf = CSRFProtect(app)

login_manager.login_view = 'homepage'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

# =========================
# Criação automática do banco (AUTO_DB_CREATE=1)
# =========================
if os.getenv('AUTO_DB_CREATE') == '1':
    try:
        with app.app_context():
            from odutech.models import Usuario  # evita import circular
            database.create_all()
            if not Usuario.query.first():
                from flask_bcrypt import generate_password_hash
                admin = Usuario(
                    username='admin',
                    email='admin@email.com',
                    senha=generate_password_hash('admin123').decode("utf-8")
                )
                database.session.add(admin)
                database.session.commit()
                print("[init] Usuário admin criado (AUTO_DB_CREATE=1).")
            print("[init] Tabelas criadas (AUTO_DB_CREATE=1).")
    except Exception as e:
        print(f"[warn] Falha ao criar tabelas automaticamente: {e}", file=sys.stderr)

# =========================
# Importar rotas
# =========================
from odutech import routes  # noqa
