from odutech import app, database, bcrypt
from odutech.models import Usuario, Cliente, Produto

with app.app_context():
    # cria TODAS as tabelas conforme o models.py (já com id_produto)
    database.create_all()
