"""
McCrea: ponto de entrada do app, organizado em MVC.

    python app.py         servidor de desenvolvimento em http://localhost:5050
    gunicorn app:app      produção (Render)

Este arquivo só monta as peças:
    models/       M: regras de negócio, banco SQLite e planilha
    views/        V: as páginas HTML (templates), entregues pelos controllers
    controllers/  C: recebem as requisições, chamam os models e respondem
    static/       CSS, JS e imagens do front-end, servidos em /static
"""
from flask import Flask

from config import Config
from controllers import registrar_controllers
from models.anuncio import Anuncio
from models.banco import init_db
from models.planilha import Planilha


def criar_app(config=Config):
    """Cria o app Flask, registra as rotas e prepara a pasta de uploads, o banco e a planilha."""
    app = Flask(__name__, template_folder="views")
    app.config.from_object(config)
    registrar_controllers(app)
    Anuncio.preparar_pasta()  # uploads/anuncios
    init_db()                 # cria/atualiza mccrea.db (dados de exemplo na primeira vez)
    Planilha.gerar()          # planilhas/usuarios.xlsx em dia com o banco
    return app


app = criar_app()

if __name__ == "__main__":
    app.run(debug=True, port=5050)
