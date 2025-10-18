# odutech/models.py
from odutech import database, login_manager
from datetime import datetime
from flask_login import UserMixin

@login_manager.user_loader
def load_usuario(id_usuario):
    return Usuario.query.get(int(id_usuario))

class Usuario(database.Model, UserMixin):
    id = database.Column(database.Integer, primary_key=True)
    username = database.Column(database.String(80), nullable=False, unique=True)
    email = database.Column(database.String(120), nullable=False, unique=True)
    senha = database.Column(database.String(200), nullable=False)
    data_criacao = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)

    # Relacionamentos
    clientes = database.relationship('Cliente', backref='usuario', lazy=True, cascade='all, delete-orphan')
    produtos = database.relationship('Produto', backref='usuario', lazy=True, cascade='all, delete-orphan')
    atendimentos = database.relationship('Atendimento', backref='usuario', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"Usuario('{self.username}', '{self.email}')"

class Cliente(database.Model):
    id = database.Column(database.Integer, primary_key=True)

    # Dados principais
    nome = database.Column(database.String(100), nullable=False)
    data_nascimento = database.Column(database.Date, nullable=False)
    nome_mae = database.Column(database.String(100), nullable=False)
    data_iniciacao = database.Column(database.Date, nullable=True)

    # Contato / endereço
    email = database.Column(database.String(120))
    telefone = database.Column(database.String(20))
    endereco = database.Column(database.Text)
    observacoes = database.Column(database.Text)

    # Campos religiosos
    navalha = database.Column(database.String(120), nullable=True)
    babakekere = database.Column(database.String(120), nullable=True)
    iyakekere = database.Column(database.String(120), nullable=True)
    ojubona = database.Column(database.String(120), nullable=True)
    padrinho = database.Column(database.String(120), nullable=True)
    madrinha = database.Column(database.String(120), nullable=True)
    orunko = database.Column(database.String(120), nullable=True)
    orixa = database.Column(database.String(120), nullable=True)
    ajunto = database.Column(database.String(120), nullable=True)
    orixas_assentados_raw = database.Column(database.Text, nullable=True)  # lista separada por vírgulas

    # Foto do cliente (caminho relativo a /static)
    foto_path = database.Column(database.String(255), nullable=True)

    data_cadastro = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)

    # FK do usuário dono
    id_usuario = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)

    # Relacionamentos
    atendimentos = database.relationship('Atendimento', backref='cliente', lazy=True, cascade='all, delete-orphan')

    # >>> NOVO: documentos do cliente <<<
    documentos = database.relationship('ClienteDocumento', backref='cliente', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f"Cliente('{self.nome}', '{self.email}')"

    def tempo_iniciacao(self):
        if self.data_iniciacao:
            hoje = datetime.now().date()
            tempo = hoje.year - self.data_iniciacao.year
            if (hoje.month, hoje.day) < (self.data_iniciacao.month, self.data_iniciacao.day):
                tempo -= 1
            return tempo
        return None

    def idade_atual(self):
        if self.data_nascimento:
            hoje = datetime.now().date()
            idade = hoje.year - self.data_nascimento.year
            if (hoje.month, hoje.day) < (self.data_nascimento.month, self.data_nascimento.day):
                idade -= 1
            return idade
        return None

class Produto(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String(100), nullable=False)
    descricao = database.Column(database.Text)
    preco = database.Column(database.Float, nullable=False, default=0.0)
    quantidade_estoque = database.Column(database.Integer, nullable=False, default=0)
    data_cadastro = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)

    id_usuario = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)

    atendimentos = database.relationship('Atendimento', backref='produto', lazy=True)

    def __repr__(self):
        return f"Produto('{self.nome}', 'R$ {self.preco:.2f}')"

class Atendimento(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    data_atendimento = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)
    executor = database.Column(database.String(100), nullable=False)
    procedimentos = database.Column(database.String(200), nullable=False)
    valor_total = database.Column(database.Float, nullable=False, default=0.0)
    forma_pagamento = database.Column(database.String(50))
    tipo_atendimento = database.Column(database.String(50), nullable=False)
    detalhes = database.Column(database.Text)

    id_usuario = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)
    id_cliente = database.Column(database.Integer, database.ForeignKey('cliente.id'), nullable=False)
    id_produto = database.Column(database.Integer, database.ForeignKey('produto.id'), nullable=True)

    def __repr__(self):
        return f"Atendimento('{self.procedimentos}', '{self.data_atendimento.strftime('%d/%m/%Y')}', 'R$ {self.valor_total:.2f}')"

# >>> NOVA TABELA: documentos anexados ao cliente <<<
class ClienteDocumento(database.Model):
    id = database.Column(database.Integer, primary_key=True)
    filename_original = database.Column(database.String(255), nullable=False)
    filename_stored = database.Column(database.String(255), nullable=False)   # caminho relativo dentro de /static/uploads/docs
    mimetype = database.Column(database.String(120), nullable=True)
    size_bytes = database.Column(database.Integer, nullable=True)
    uploaded_at = database.Column(database.DateTime, nullable=False, default=datetime.utcnow)

    id_usuario = database.Column(database.Integer, database.ForeignKey('usuario.id'), nullable=False)
    id_cliente = database.Column(database.Integer, database.ForeignKey('cliente.id'), nullable=False)

    def __repr__(self):
        return f"ClienteDocumento('{self.filename_original}', cliente={self.id_cliente})"
