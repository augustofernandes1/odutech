from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, SubmitField, TextAreaField,
    SelectField, DecimalField, IntegerField, DateField
)
from wtforms.validators import DataRequired, Email, Length, ValidationError, Optional, NumberRange
from datetime import datetime, date
from flask_wtf.file import FileField, FileAllowed, FileRequired


class FormLogin(FlaskForm):
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    senha = PasswordField('Senha', validators=[DataRequired()])
    botao_confirmacao = SubmitField('Fazer Login')


class FormCliente(FlaskForm):
    nome = StringField('Nome Completo', validators=[DataRequired(), Length(max=100)])
    data_nascimento = DateField('Data de Nascimento', validators=[DataRequired()], format='%Y-%m-%d')
    nome_mae = StringField('Primeiro Nome da Mãe', validators=[DataRequired(), Length(max=100)])
    data_iniciacao = DateField('Data de Iniciação (opcional)', validators=[Optional()], format='%Y-%m-%d')
    email = StringField('E-mail (opcional)', validators=[Optional(), Email(), Length(max=120)])
    telefone = StringField('Telefone (opcional)', validators=[Optional(), Length(max=20)])
    endereco = TextAreaField('Endereço (opcional)', validators=[Optional()])
    observacoes = TextAreaField('Observações (opcional)', validators=[Optional()])

    # >>> AQUI: FileField para aceitar imagem <<<
    foto = FileField(
        'Foto do Cliente (JPG/PNG)',
        validators=[
            Optional(),
            FileAllowed(['jpg', 'jpeg', 'png'], 'Apenas imagens JPG ou PNG.')
        ]
    )

    botao_confirmacao = SubmitField('Salvar Cliente')

    def validate_data_nascimento(self, field):
        if not field.data:
            raise ValidationError('A data de nascimento é obrigatória.')
        if field.data > date.today():
            raise ValidationError('A data de nascimento não pode ser no futuro.')

    def validate_data_iniciacao(self, field):
        if field.data:
            if field.data > date.today():
                raise ValidationError('A data de iniciação não pode ser no futuro.')
            if (self.data_nascimento.data and field.data < self.data_nascimento.data):
                raise ValidationError('A data de iniciação não pode ser anterior à data de nascimento.')

    def validate_nome_mae(self, field):
        if not field.data:
            raise ValidationError('O nome da mãe é obrigatório.')


class FormProduto(FlaskForm):
    nome = StringField('Nome do Produto', validators=[DataRequired(), Length(max=100)])
    descricao = TextAreaField('Descrição', validators=[Optional()])
    preco = DecimalField('Preço', validators=[DataRequired(), NumberRange(min=0)], places=2)
    quantidade_estoque = IntegerField('Quantidade em Estoque', validators=[DataRequired(), NumberRange(min=0)], default=0)
    botao_confirmacao = SubmitField('Salvar Produto')


class FormAtendimento(FlaskForm):
    data_atendimento = DateField('Data do Atendimento', validators=[DataRequired()], default=datetime.now, format='%Y-%m-%d')
    id_cliente = SelectField('Cliente', coerce=int, validators=[DataRequired()])
    id_produto = SelectField('Produto', coerce=int, validators=[DataRequired()])
    executor = StringField('Executor', validators=[DataRequired(), Length(max=100)])
    procedimentos = TextAreaField('Procedimentos', validators=[DataRequired(), Length(max=200)])
    valor_total = DecimalField('Valor Total', validators=[DataRequired(), NumberRange(min=0)], places=2)
    forma_pagamento = SelectField(
        'Forma de Pagamento',
        choices=[
            ('', 'Selecione...'),
            ('dinheiro', 'Dinheiro'),
            ('pix', 'PIX'),
            ('cartao_credito', 'Cartão de Crédito'),
            ('cartao_debito', 'Cartão de Débito'),
            ('transferencia', 'Transferência Bancária')
        ],
        validators=[DataRequired()]
    )
    tipo_atendimento = SelectField(
        'Tipo de Atendimento',
        choices=[
            ('', 'Selecione...'),
            ('consulta', 'Consulta'),
            ('ebó', 'Ebó'),
            ('gbory', 'Gbory'),
            ('obrigacao', 'Obrigação'),
            ('buzios', 'Búzios'),
            ('outro', 'Outro')
        ],
        validators=[DataRequired()]
    )
    detalhes = TextAreaField('Detalhes', validators=[Optional()])
    botao_confirmacao = SubmitField('Salvar Atendimento')

    def validate_id_cliente(self, field):
        if field.data == 0:
            raise ValidationError('Por favor, selecione um cliente válido.')

    def validate_id_produto(self, field):
        if field.data == 0:
            raise ValidationError('Por favor, selecione um produto válido.')


class FormClienteRituais(FlaskForm):
    navalha = StringField('Navalha (Quem Iniciou)', validators=[Optional(), Length(max=120)])
    babakekere = StringField('Babakekere (Pai Pequeno)', validators=[Optional(), Length(max=120)])
    iyakekere = StringField('Iyakekere (Mãe Pequena)', validators=[Optional(), Length(max=120)])
    ojubona = StringField('Ojubonã (Pai/Mãe Criador[a])', validators=[Optional(), Length(max=120)])
    padrinho = StringField('Padrinho de Orunkó', validators=[Optional(), Length(max=120)])
    madrinha = StringField('Madrinha de Orunkó', validators=[Optional(), Length(max=120)])

    orunko = StringField('Orunkó', validators=[Optional(), Length(max=120)])
    orixa = StringField('Orixá Orí', validators=[Optional(), Length(max=120)])
    ajunto = StringField('Orixá Ajuntó', validators=[Optional(), Length(max=120)])

    orixas_assentados_raw = TextAreaField(
        'Orixás Assentados (separe por vírgula)',
        validators=[Optional(), Length(max=600)],
        render_kw={"rows": 2, "placeholder": "Ex.: Xangô, Oxum, Ogum"}
    )

    submit = SubmitField('Salvar Rituais')


class FormClienteDocumento(FlaskForm):
    arquivo = FileField(
        'Anexar documento (PDF/DOC/DOCX)',
        validators=[
            FileRequired(message='Selecione um arquivo.'),
            FileAllowed(['pdf', 'doc', 'docx'], 'Somente PDF, DOC ou DOCX.')
        ]
    )
    descricao = StringField('Descrição (opcional)', validators=[Optional(), Length(max=120)])
    submit = SubmitField('Anexar')
