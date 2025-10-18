from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_wtf.csrf import CSRFProtect
import os, sys

app = Flask(__name__)

# ---- Secrets / base ----
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', '5563bafbd7bald301ca61fc591227446')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ---- Banco (SQLite em Volume) ----
# Em produção: DATABASE_URL = sqlite:////data/comunidade.db
DB_URL = os.getenv('DATABASE_URL', 'sqlite:///comunidade.db')
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URL

# ---- Uploads persistentes ----
# Em produção: VOLUME_DIR = /data
VOLUME_DIR = os.getenv('VOLUME_DIR')
if VOLUME_DIR:
    BASE_UPLOADS = os.path.join(VOLUME_DIR, 'uploads')   # /data/uploads
else:
    BASE_UPLOADS = os.path.join(app.root_path, 'static', 'uploads')  # local

os.makedirs(BASE_UPLOADS, exist_ok=True)
app.config['UPLOAD_PHOTOS_FOLDER'] = os.path.join(BASE_UPLOADS, 'fotos')
app.config['UPLOAD_DOCS_FOLDER']   = os.path.join(BASE_UPLOADS, 'docs')
for p in (app.config['UPLOAD_PHOTOS_FOLDER'], app.config['UPLOAD_DOCS_FOLDER']):
    os.makedirs(p, exist_ok=True)

app.config['UPLOADS_ROOT'] = BASE_UPLOADS
app.config.setdefault('MAX_CONTENT_LENGTH', 16 * 1024 * 1024)

# ---- Symlink opcional: /static/uploads -> Volume ----
try:
    static_uploads = os.path.join(app.root_path, 'static', 'uploads')
    if not os.path.exists(static_uploads):
        if VOLUME_DIR and os.name != 'nt':
            os.makedirs(os.path.join(app.root_path, 'static'), exist_ok=True)
            os.symlink(BASE_UPLOADS, static_uploads)
        else:
            os.makedirs(static_uploads, exist_ok=True)
except Exception as e:
    print(f"[warn] Falha ao criar symlink de uploads: {e}", file=sys.stderr)

# ---- Extensões ----
database = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
csrf = CSRFProtect(app)
login_manager.login_view = 'homepage'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

# ---- Auto-create DB (opcional, útil no primeiro start em produção) ----
# Ative com AUTO_DB_CREATE=1 no Railway
if os.getenv('AUTO_DB_CREATE') == '1':
    try:
        with app.app_context():
            database.create_all()
            print("[init] Tabelas criadas (AUTO_DB_CREATE=1).")
    except Exception as e:
        print(f"[warn] Falha ao criar tabelas automaticamente: {e}", file=sys.stderr)

# Importar rotas no final
from odutech import routes  # noqa
