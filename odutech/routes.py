# odutech/routes.py
from flask import render_template, redirect, url_for, flash, request, send_from_directory, abort
from odutech import app, database, bcrypt
from odutech.models import Usuario, Atendimento, Cliente, Produto, ClienteDocumento
from odutech.forms import (
    FormLogin, FormCliente, FormProduto, FormAtendimento, FormClienteRituais, FormClienteDocumento
)
from flask_login import login_user, logout_user, login_required, current_user
from datetime import datetime
from sqlalchemy import or_
from flask_wtf.csrf import CSRFError
import calendar
import unicodedata
import os
import uuid
from werkzeug.utils import secure_filename


# ==============================
# UTILS
# ==============================
def _norm(s: str) -> str:
    """Normaliza string: minúscula e sem acentos."""
    if not s:
        return ""
    s = s.lower()
    return "".join(ch for ch in unicodedata.normalize("NFD", s)
                   if unicodedata.category(ch) != "Mn")


def _cliente_docs_dir(user_id: int, cliente_id: int) -> str:
    """Diretório físico para documentos do cliente dentro de static/uploads/docs/uX/cY."""
    base = app.config['UPLOAD_DOCS_FOLDER']  # .../static/uploads/docs
    d = os.path.join(base, f"u{user_id}", f"c{cliente_id}")
    os.makedirs(d, exist_ok=True)
    return d


def _save_file_to(dir_path: str, file_storage, filename: str = None) -> (str, str):
    """
    Salva um FileStorage em 'dir_path' com nome único.
    Retorna (abs_path, stored_name).
    """
    os.makedirs(dir_path, exist_ok=True)
    original = secure_filename(filename or (file_storage.filename or "arquivo"))
    ext = os.path.splitext(original)[1].lower()
    unique = uuid.uuid4().hex
    stored_name = f"{unique}{ext}"
    abs_path = os.path.join(dir_path, stored_name)
    file_storage.save(abs_path)
    return abs_path, stored_name


def _save_photo(file_storage, cliente_id: int) -> str:
    """
    Salva a foto do cliente em static/uploads/fotos.
    Retorna o caminho relativo a /static para armazenar no banco (foto_path).
    """
    photos_dir = app.config['UPLOAD_PHOTOS_FOLDER']  # .../static/uploads/fotos
    # opcional: subpastas por cliente
    photos_dir = os.path.join(photos_dir, f"c{cliente_id}")
    abs_path, stored_name = _save_file_to(photos_dir, file_storage)
    rel_path = os.path.relpath(abs_path, os.path.join(app.root_path, 'static')).replace("\\", "/")
    return rel_path


# ==============================
# HANDLERS GLOBAIS
# ==============================
@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash('Sua sessão expirou ou a requisição é inválida. Tente novamente.', 'warning')
    return redirect(request.referrer or url_for('homepage'))


# ==============================
# LOGIN / LOGOUT
# ==============================
@app.route('/', methods=['GET', 'POST'])
def homepage():
    form_login = FormLogin()

    if form_login.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form_login.email.data).first()
        if usuario and bcrypt.check_password_hash(usuario.senha, form_login.senha.data):
            login_user(usuario)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('perfil', id_usuario=usuario.id))
        else:
            flash('E-mail ou senha incorretos.', 'danger')

    return render_template('homepage.html', form=form_login)


@app.route('/sair')
@login_required
def sair():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'info')
    return redirect(url_for('homepage'))


# ==============================
# DASHBOARD / PERFIL
# ==============================
@app.route('/perfil/<int:id_usuario>')
@login_required
def perfil(id_usuario):
    if current_user.id != id_usuario:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('perfil', id_usuario=current_user.id))

    usuario = Usuario.query.get_or_404(id_usuario)
    hoje = datetime.now()
    ano, mes = hoje.year, hoje.month

    primeiro_dia_mes = datetime(ano, mes, 1)
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    ultimo_dia_mes = datetime(ano, mes, ultimo_dia, 23, 59, 59)

    atendimentos_mes = (
        Atendimento.query.filter(
            Atendimento.id_usuario == usuario.id,
            Atendimento.data_atendimento >= primeiro_dia_mes,
            Atendimento.data_atendimento <= ultimo_dia_mes
        )
        .order_by(Atendimento.data_atendimento.desc())
        .all()
    )

    total_atendimentos = len(atendimentos_mes)
    valor_total_mes = sum(a.valor_total or 0 for a in atendimentos_mes)

    ebos_mes = len([a for a in atendimentos_mes if 'ebo' in _norm(a.tipo_atendimento)])
    gbory_mes = len([a for a in atendimentos_mes if 'gbory' in _norm(a.tipo_atendimento)])
    obrigacao_mes = len([a for a in atendimentos_mes if 'obrig' in _norm(a.tipo_atendimento)])
    buzios_mes = len([a for a in atendimentos_mes if 'buzio' in _norm(a.tipo_atendimento)])

    return render_template(
        'perfil.html',
        usuario=usuario,
        atendimentos=atendimentos_mes,
        total_atendimentos=total_atendimentos,
        ebos_mes=ebos_mes,
        gbory_mes=gbory_mes,
        obrigacao_mes=obrigacao_mes,
        buzios_mes=buzios_mes,
        valor_total_mes=valor_total_mes,
        now=datetime.now()
    )


# ==============================
# CLIENTES
# ==============================
@app.route('/clientes', methods=['GET'])
@login_required
def clientes():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    query = Cliente.query.filter_by(id_usuario=current_user.id)

    if search:
        query = query.filter(
            or_(
                Cliente.nome.ilike(f'%{search}%'),
                Cliente.email.ilike(f'%{search}%'),
                Cliente.telefone.ilike(f'%{search}%')
            )
        )

    clientes_pag = query.order_by(Cliente.nome.asc()).paginate(page=page, per_page=10)

    return render_template('clientes.html', clientes=clientes_pag, search=search, now=datetime.now())


@app.route('/cliente/novo', methods=['GET', 'POST'])
@login_required
def novo_cliente():
    form = FormCliente()
    if form.validate_on_submit():
        try:
            cliente = Cliente(
                nome=form.nome.data,
                data_nascimento=form.data_nascimento.data,
                nome_mae=form.nome_mae.data,
                data_iniciacao=form.data_iniciacao.data,
                email=form.email.data,
                telefone=form.telefone.data,
                endereco=form.endereco.data,
                observacoes=form.observacoes.data,
                id_usuario=current_user.id
            )
            database.session.add(cliente)
            database.session.commit()

            # Foto (se enviada)
            if hasattr(form, 'foto') and form.foto.data:
                try:
                    rel_path = _save_photo(form.foto.data, cliente.id)
                    cliente.foto_path = rel_path
                    database.session.commit()
                except Exception as e:
                    database.session.rollback()
                    flash(f'Cliente salvo. Falha ao salvar foto: {e}', 'warning')

            flash('Cliente cadastrado com sucesso!', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            database.session.rollback()
            flash(f'Erro: {e}', 'danger')

    return render_template('form_cliente.html', form=form, title='Novo Cliente', now=datetime.now())


@app.route('/cliente/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    cliente = Cliente.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    form = FormCliente(obj=cliente)

    if form.validate_on_submit():
        try:
            cliente.nome = form.nome.data
            cliente.data_nascimento = form.data_nascimento.data
            cliente.nome_mae = form.nome_mae.data
            cliente.data_iniciacao = form.data_iniciacao.data
            cliente.email = form.email.data
            cliente.telefone = form.telefone.data
            cliente.endereco = form.endereco.data
            cliente.observacoes = form.observacoes.data

            # Atualiza foto se enviada
            if hasattr(form, 'foto') and form.foto.data:
                try:
                    rel_path = _save_photo(form.foto.data, cliente.id)
                    cliente.foto_path = rel_path
                except Exception as e:
                    flash(f'Falha ao atualizar a foto: {e}', 'warning')

            database.session.commit()
            flash('Cliente atualizado com sucesso!', 'success')
            return redirect(url_for('clientes'))
        except Exception as e:
            database.session.rollback()
            flash(f'Erro ao salvar alterações: {e}', 'danger')

    return render_template('form_cliente.html', form=form, title='Editar Cliente', cliente=cliente, now=datetime.now())


@app.route('/cliente/excluir/<int:id>', methods=['POST', 'GET'])
@login_required
def excluir_cliente(id):
    if request.method != 'POST':
        flash('Use o botão "Excluir" para remover um cliente.', 'info')
        return redirect(url_for('clientes'))

    cliente = Cliente.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()

    if Atendimento.query.filter_by(id_cliente=id).count() > 0:
        flash('Não é possível excluir um cliente com atendimentos.', 'danger')
        return redirect(url_for('clientes'))

    database.session.delete(cliente)
    database.session.commit()
    flash('Cliente excluído com sucesso!', 'success')
    return redirect(url_for('clientes'))


# --------- Detalhes do Cliente + Rituais + Documentos ----------
@app.route('/cliente/<int:id>')
@login_required
def cliente_detalhes(id):
    cliente = Cliente.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    atendimentos = Atendimento.query.filter_by(id_cliente=id).order_by(Atendimento.data_atendimento.desc()).all()

    # Documentos do cliente
    documentos = (ClienteDocumento.query
                  .filter_by(id_cliente=id, id_usuario=current_user.id)
                  .order_by(ClienteDocumento.uploaded_at.desc())
                  .all())

    form_rituais = FormClienteRituais(obj=cliente)  # útil se quiser embutir edição na mesma página
    form_doc = FormClienteDocumento()

    return render_template(
        'cliente_detalhes.html',
        cliente=cliente,
        atendimentos=atendimentos,
        documentos=documentos,
        form=form_rituais,
        form_doc=form_doc,
        now=datetime.now()
    )


@app.route('/cliente/<int:id>/novo-atendimento')
@login_required
def cliente_novo_atendimento(id):
    """Atalho para abrir o formulário já com o cliente pré-selecionado."""
    return redirect(url_for('novo_atendimento', cliente_id=id))


@app.route('/cliente/<int:id>/rituais', methods=['GET', 'POST'])
@login_required
def cliente_rituais(id):
    cliente = Cliente.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    form = FormClienteRituais(obj=cliente)

    if request.method == 'POST':
        if form.validate_on_submit():
            cliente.navalha = form.navalha.data
            cliente.babakekere = form.babakekere.data
            cliente.iyakekere = form.iyakekere.data
            cliente.ojubona = form.ojubona.data
            cliente.padrinho = form.padrinho.data
            cliente.madrinha = form.madrinha.data
            cliente.orixa = form.orixa.data
            cliente.ajunto = form.ajunto.data
            # Se você também adicionou Orunkó e orixás assentados no form dedicado, trate aqui:
            if hasattr(form, 'orunko'):
                cliente.orunko = form.orunko.data
            if hasattr(form, 'orixas_assentados_raw'):
                cliente.orixas_assentados_raw = form.orixas_assentados_raw.data

            database.session.commit()
            flash('Ficha ritual salva com sucesso!', 'success')
            return redirect(url_for('cliente_detalhes', id=cliente.id))
        else:
            flash('Verifique os campos da ficha ritual.', 'warning')

    return render_template('form_rituais.html', form=form, cliente=cliente, now=datetime.now())


# ====== Upload / Download / Exclusão de documentos ======
@app.route('/cliente/<int:id>/documento/upload', methods=['POST'])
@login_required
def cliente_upload_documento(id):
    cliente = Cliente.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    form_doc = FormClienteDocumento()

    if not form_doc.validate_on_submit():
        atendimentos = Atendimento.query.filter_by(id_cliente=id).order_by(Atendimento.data_atendimento.desc()).all()
        documentos = (ClienteDocumento.query
                      .filter_by(id_cliente=id, id_usuario=current_user.id)
                      .order_by(ClienteDocumento.uploaded_at.desc())
                      .all())
        form_rituais = FormClienteRituais(obj=cliente)
        flash('Verifique o arquivo selecionado.', 'warning')
        return render_template('cliente_detalhes.html',
                               cliente=cliente,
                               atendimentos=atendimentos,
                               documentos=documentos,
                               form=form_rituais,
                               form_doc=form_doc,
                               now=datetime.now())

    f = form_doc.arquivo.data
    filename_orig = secure_filename(f.filename or '')
    if not filename_orig:
        flash('Nome de arquivo inválido.', 'danger')
        return redirect(url_for('cliente_detalhes', id=cliente.id))

    target_dir = _cliente_docs_dir(current_user.id, cliente.id)
    abs_path, stored_name = _save_file_to(target_dir, f, filename_orig)

    rel_path = os.path.relpath(abs_path, os.path.join(app.root_path, 'static')).replace('\\', '/')
    size_bytes = os.path.getsize(abs_path)
    mimetype = f.mimetype

    doc = ClienteDocumento(
        filename_original=filename_orig,
        filename_stored=rel_path,
        mimetype=mimetype,
        size_bytes=size_bytes,
        id_usuario=current_user.id,
        id_cliente=cliente.id
    )
    database.session.add(doc)
    database.session.commit()
    flash('Documento anexado com sucesso!', 'success')
    return redirect(url_for('cliente_detalhes', id=cliente.id))


@app.route('/cliente/documento/<int:doc_id>/download')
@login_required
def cliente_download_documento(doc_id):
    doc = ClienteDocumento.query.get_or_404(doc_id)
    if doc.id_usuario != current_user.id:
        abort(403)

    abs_path = os.path.join(app.root_path, 'static', doc.filename_stored)
    if not os.path.isfile(abs_path):
        flash('Arquivo não encontrado no servidor.', 'danger')
        return redirect(url_for('cliente_detalhes', id=doc.id_cliente))

    directory = os.path.dirname(abs_path)
    filename = os.path.basename(abs_path)
    return send_from_directory(directory=directory, path=filename, as_attachment=True, download_name=doc.filename_original)


@app.route('/cliente/documento/<int:doc_id>/excluir', methods=['POST'])
@login_required
def cliente_excluir_documento(doc_id):
    doc = ClienteDocumento.query.get_or_404(doc_id)
    if doc.id_usuario != current_user.id:
        abort(403)

    abs_path = os.path.join(app.root_path, 'static', doc.filename_stored)
    try:
        if os.path.isfile(abs_path):
            os.remove(abs_path)
    except Exception:
        pass

    id_cliente = doc.id_cliente
    database.session.delete(doc)
    database.session.commit()
    flash('Documento excluído.', 'info')
    return redirect(url_for('cliente_detalhes', id=id_cliente))


# ==============================
# PRODUTOS
# ==============================
@app.route('/produtos', methods=['GET'])
@login_required
def produtos():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')

    query = Produto.query.filter_by(id_usuario=current_user.id)
    if search:
        query = query.filter(
            or_(
                Produto.nome.ilike(f'%{search}%'),
                Produto.descricao.ilike(f'%{search}%')
            )
        )

    produtos_pag = query.order_by(Produto.nome.asc()).paginate(page=page, per_page=10)
    return render_template('produtos.html', produtos=produtos_pag, search=search, now=datetime.now())


@app.route('/produto/novo', methods=['GET', 'POST'])
@login_required
def novo_produto():
    form = FormProduto()
    if form.validate_on_submit():
        produto = Produto(
            nome=form.nome.data,
            descricao=form.descricao.data,
            preco=float(form.preco.data or 0),
            quantidade_estoque=int(form.quantidade_estoque.data or 0),
            id_usuario=current_user.id
        )
        database.session.add(produto)
        database.session.commit()
        flash('Produto cadastrado com sucesso!', 'success')
        return redirect(url_for('produtos'))
    return render_template('form_produto.html', form=form, title='Novo Produto', now=datetime.now())


@app.route('/produto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_produto(id):
    produto = Produto.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    form = FormProduto(obj=produto)
    if form.validate_on_submit():
        produto.nome = form.nome.data
        produto.descricao = form.descricao.data
        produto.preco = float(form.preco.data or 0)
        produto.quantidade_estoque = int(form.quantidade_estoque.data or 0)
        database.session.commit()
        flash('Produto atualizado com sucesso!', 'success')
        return redirect(url_for('produtos'))
    return render_template('form_produto.html', form=form, title='Editar Produto', produto=produto, now=datetime.now())


@app.route('/produto/excluir/<int:id>', methods=['POST', 'GET'])
@login_required
def excluir_produto(id):
    if request.method != 'POST':
        flash('Use o botão "Excluir" para remover um produto.', 'info')
        return redirect(url_for('produtos'))

    produto = Produto.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    database.session.delete(produto)
    database.session.commit()
    flash('Produto excluído com sucesso!', 'success')
    return redirect(url_for('produtos'))


# ==============================
# ATENDIMENTOS
# ==============================
def _fill_atendimento_selects(form):
    clientes_choices = [(0, 'Selecione...')] + [
        (c.id, c.nome) for c in
        Cliente.query.filter_by(id_usuario=current_user.id).order_by(Cliente.nome.asc()).all()
    ]
    produtos_choices = [(0, 'Selecione...')] + [
        (p.id, p.nome) for p in
        Produto.query.filter_by(id_usuario=current_user.id).order_by(Produto.nome.asc()).all()
    ]

    if hasattr(form, 'id_cliente'):
        form.id_cliente.choices = clientes_choices
    if hasattr(form, 'id_produto'):
        form.id_produto.choices = produtos_choices


@app.route('/atendimentos', methods=['GET'])
@login_required
def atendimentos_lista():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    mes = request.args.get('mes', '')

    query = Atendimento.query.filter_by(id_usuario=current_user.id)

    if search:
        query = query.join(Cliente).filter(
            or_(
                Cliente.nome.ilike(f'%{search}%'),
                Atendimento.procedimentos.ilike(f'%{search}%')
            )
        )

    if mes:
        try:
            mes_num = int(mes)
            query = query.filter(
                database.extract('month', Atendimento.data_atendimento) == mes_num
            )
        except ValueError:
            pass

    atendimentos_pag = query.order_by(Atendimento.data_atendimento.desc()).paginate(page=page, per_page=10)
    total_vendas = sum(a.valor_total or 0 for a in atendimentos_pag.items)
    total_atendimentos = atendimentos_pag.total
    ticket_medio = (total_vendas / total_atendimentos) if total_atendimentos else 0.0

    return render_template('atendimentos.html',
                           atendimentos=atendimentos_pag,
                           search=search,
                           mes=mes,
                           total_vendas=total_vendas,
                           total_atendimentos=total_atendimentos,
                           ticket_medio=ticket_medio,
                           now=datetime.now())


@app.route('/atendimento/novo', methods=['GET', 'POST'])
@login_required
def novo_atendimento():
    form = FormAtendimento()
    _fill_atendimento_selects(form)

    # Pré-seleciona cliente se vier via /cliente/<id>/novo-atendimento
    cliente_id_arg = request.args.get('cliente_id', type=int)
    if cliente_id_arg and hasattr(form, 'id_cliente'):
        ids_disponiveis = {cid for cid, _ in form.id_cliente.choices}
        form.id_cliente.data = cliente_id_arg if cliente_id_arg in ids_disponiveis else 0

    if form.validate_on_submit():
        atendimento = Atendimento(
            data_atendimento=form.data_atendimento.data,
            id_cliente=form.id_cliente.data if form.id_cliente.data != 0 else None,
            id_produto=form.id_produto.data if form.id_produto.data != 0 else None,
            executor=form.executor.data,
            procedimentos=form.procedimentos.data,
            valor_total=float(form.valor_total.data or 0),
            forma_pagamento=form.forma_pagamento.data,
            tipo_atendimento=form.tipo_atendimento.data,
            detalhes=form.detalhes.data,
            id_usuario=current_user.id
        )
        database.session.add(atendimento)
        database.session.commit()
        flash('Atendimento registrado com sucesso!', 'success')
        return redirect(url_for('atendimentos_lista'))

    if not form.data_atendimento.data:
        form.data_atendimento.data = datetime.now()

    return render_template('form_atendimento.html', form=form, title='Novo Atendimento', now=datetime.now())


@app.route('/atendimento/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_atendimento(id):
    atendimento = Atendimento.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    form = FormAtendimento(obj=atendimento)
    _fill_atendimento_selects(form)

    form.id_cliente.data = atendimento.id_cliente or 0
    form.id_produto.data = atendimento.id_produto or 0

    if form.validate_on_submit():
        atendimento.data_atendimento = form.data_atendimento.data
        atendimento.id_cliente = form.id_cliente.data if form.id_cliente.data != 0 else None
        atendimento.id_produto = form.id_produto.data if form.id_produto.data != 0 else None
        atendimento.executor = form.executor.data
        atendimento.procedimentos = form.procedimentos.data
        atendimento.valor_total = float(form.valor_total.data or 0)
        atendimento.forma_pagamento = form.forma_pagamento.data
        atendimento.tipo_atendimento = form.tipo_atendimento.data
        atendimento.detalhes = form.detalhes.data
        database.session.commit()
        flash('Atendimento atualizado com sucesso!', 'success')
        return redirect(url_for('atendimentos_lista'))

    return render_template('form_atendimento.html', form=form, title='Editar Atendimento', atendimento=atendimento, now=datetime.now())


@app.route('/atendimento/excluir/<int:id>', methods=['POST', 'GET'])
@login_required
def excluir_atendimento(id):
    if request.method != 'POST':
        flash('Use o botão "Excluir" para remover um atendimento.', 'info')
        return redirect(url_for('atendimentos_lista'))

    atendimento = Atendimento.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    database.session.delete(atendimento)
    database.session.commit()
    flash('Atendimento excluído com sucesso!', 'success')
    return redirect(url_for('atendimentos_lista'))


@app.route('/atendimento/<int:id>')
@login_required
def detalhes_atendimento(id):
    atendimento = Atendimento.query.filter_by(id=id, id_usuario=current_user.id).first_or_404()
    return render_template('detalhes_atendimento.html', atendimento=atendimento, now=datetime.now())


# ==============================
# RELATÓRIOS
# ==============================
@app.route('/relatorios/vendas')
@login_required
def relatorios_vendas():
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    tipo = request.args.get('tipo', '')

    query = Atendimento.query.filter_by(id_usuario=current_user.id)

    if data_inicio:
        try:
            di = datetime.strptime(data_inicio, '%Y-%m-%d')
            query = query.filter(Atendimento.data_atendimento >= di)
        except ValueError:
            pass

    if data_fim:
        try:
            df = datetime.strptime(data_fim, '%Y-%m-%d')
            query = query.filter(Atendimento.data_atendimento <= df)
        except ValueError:
            pass

    if tipo:
        query = query.filter(Atendimento.tipo_atendimento == tipo)

    vendas = query.order_by(Atendimento.data_atendimento.desc()).all()
    total_vendas = sum(v.valor_total or 0 for v in vendas)
    total_atendimentos = len(vendas)

    estatisticas = {}
    for t in ['ebó', 'gbory', 'obrigacao', 'obrigação', 'buzios', 'outro']:
        estatisticas[t] = {
            'quantidade': len([v for v in vendas if _norm(v.tipo_atendimento) == _norm(t)]),
            'valor_total': sum(v.valor_total or 0 for v in vendas if _norm(v.tipo_atendimento) == _norm(t))
        }

    return render_template('relatorios_vendas.html',
                           vendas=vendas,
                           total_vendas=total_vendas,
                           total_atendimentos=total_atendimentos,
                           estatisticas=estatisticas,
                           data_inicio=data_inicio,
                           data_fim=data_fim,
                           tipo=tipo,
                           now=datetime.now())
