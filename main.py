from odutech import app, database
from flask_bcrypt import generate_password_hash

# ==== MODELO DO USUÁRIO ====
try:
    from odutech.models import Usuario
except Exception:
    from models import Usuario

# ==== IMPORTS CLI ====
import argparse
import getpass

# =============================================================================
# UTILITÁRIOS PARA USUÁRIOS (CLI)
# =============================================================================

def add_user(username: str, email: str, password: str):
    """Cria um novo usuário com verificação de unicidade e hash de senha."""
    ja_existe = Usuario.query.filter(
        (Usuario.username == username) | (Usuario.email == email)
    ).first()
    if ja_existe:
        raise ValueError("Já existe um usuário com esse username ou e-mail.")

    user = Usuario(
        username=username.strip(),
        email=email.strip(),
        senha=generate_password_hash(password).decode("utf-8")
    )
    database.session.add(user)
    database.session.commit()
    return user


def list_users():
    """Retorna todos os usuários cadastrados."""
    return [(u.username, u.email) for u in Usuario.query.order_by(Usuario.username).all()]


def ensure_admin_seed():
    """Cria o usuário admin padrão caso ainda não exista."""
    if not Usuario.query.first():
        admin = Usuario(
            username='admin',
            email='admin@email.com',
            senha=generate_password_hash('admin123').decode("utf-8")
        )
        database.session.add(admin)
        database.session.commit()
        print("✅ Usuário admin criado:")
        print("   • Email: admin@email.com")
        print("   • Senha: admin123")


def run_cli_tools():
    """Ferramentas de linha de comando: criar e listar usuários."""
    parser = argparse.ArgumentParser(description="Gerenciar usuários do sistema")
    parser.add_argument("--add-user", action="store_true", help="Adicionar novo usuário")
    parser.add_argument("--list-users", action="store_true", help="Listar usuários existentes")
    args, _ = parser.parse_known_args()

    if args.add_user:
        print("➕ Criar novo usuário")
        username = input("Username: ").strip()
        email = input("E-mail: ").strip()
        pwd = getpass.getpass("Senha: ")
        pwd2 = getpass.getpass("Confirmar senha: ")
        if pwd != pwd2:
            print("❌ Senhas não conferem.")
            return
        try:
            user = add_user(username, email, pwd)
            print(f"✅ Usuário criado com sucesso: {user.username} <{user.email}>")
        except ValueError as e:
            print(f"⚠️  {e}")
        return

    if args.list_users:
        usuarios = list_users()
        if not usuarios:
            print("ℹ️  Nenhum usuário cadastrado.")
        else:
            print("👥 Usuários existentes:")
            for u, e in usuarios:
                print(f" - {u:<20} {e}")
        return

# =============================================================================
# INICIALIZAÇÃO PRINCIPAL DO APP
# =============================================================================

if __name__ == "__main__":
    with app.app_context():
        # Criar banco de dados
        database.create_all()
        print("✅ Banco de dados criado com sucesso!")

        # Garantir o admin padrão
        ensure_admin_seed()

        # Executar CLI se houver argumentos
        run_cli_tools()

    # Iniciar servidor Flask
    app.run(debug=True)
