"""
Controllers (o C do MVC): recebem a requisição HTTP, chamam o Model e respondem com JSON
ou com uma View (template de views/).

Este arquivo é a tabela de rotas do app. Cada rota mantém a mesma URL, o mesmo método e o
MESMO nome de endpoint de antes da organização em MVC: as Views usam url_for('index') e
url_for('app_principal'), e o front-end chama as URLs da API diretamente.
"""
from controllers import (admin_controller, anuncios_controller, conta_controller, cupons_controller,
                         depositos_controller, maquinas_controller, paginas_controller)
from controllers.respostas import resposta_de_erro, upload_grande
from models.anuncio import URL_ANUNCIOS
from models.banco import fechar_db
from models.erros import ErroDeNegocio

# (método, URL, nome do endpoint, função do controller)
ROTAS = [
    # Páginas (Views)
    ("GET", "/", "index", paginas_controller.index),
    ("GET", "/app", "app_principal", paginas_controller.app_principal),
    # Administrador
    ("GET", "/api/admin/painel", "admin_painel", admin_controller.admin_painel),
    ("GET", "/api/admin/planilha", "baixar_planilha", admin_controller.baixar_planilha),
    ("GET", "/api/analise", "analise", admin_controller.analise),
    # Máquinas
    ("GET", "/api/maquinas", "listar_maquinas", maquinas_controller.listar_maquinas),
    ("POST", "/api/maquinas", "criar_maquina", maquinas_controller.criar_maquina),
    ("GET", "/api/maquinas/proximas", "maquinas_proximas", maquinas_controller.maquinas_proximas),
    # Conta: cadastro, login e endereço
    ("POST", "/api/cadastro", "cadastro", conta_controller.cadastro),
    ("POST", "/api/login", "login", conta_controller.login),
    ("POST", "/api/logout", "logout", conta_controller.logout),
    ("POST", "/api/eu/endereco", "mudar_endereco", conta_controller.mudar_endereco),
    ("GET", "/api/eu", "progresso", conta_controller.progresso),
    # Depósitos
    ("POST", "/api/depositos", "depositar", depositos_controller.depositar),
    # Cupons
    ("GET", "/api/cupons", "listar_cupons", cupons_controller.listar_cupons),
    ("POST", "/api/cupons", "criar_cupom", cupons_controller.criar_cupom),
    ("POST", "/api/resgatar", "resgatar", cupons_controller.resgatar),
    # Notícias: anúncios com cartaz (carrossel)
    ("GET", URL_ANUNCIOS + "<path:nome>", "cartaz", anuncios_controller.cartaz),
    ("GET", "/api/anuncios", "listar_anuncios", anuncios_controller.listar_anuncios),
    ("GET", "/api/anuncios/<int:aid>", "ver_anuncio", anuncios_controller.ver_anuncio),
    ("GET", "/api/admin/anuncios", "listar_anuncios_admin", anuncios_controller.listar_anuncios_admin),
    ("POST", "/api/anuncios", "criar_anuncio", anuncios_controller.criar_anuncio),
    ("PUT", "/api/anuncios/<int:aid>", "editar_anuncio", anuncios_controller.editar_anuncio),
    ("DELETE", "/api/anuncios/<int:aid>", "excluir_anuncio", anuncios_controller.excluir_anuncio),
]


def registrar_controllers(app):
    """Liga cada URL ao seu controller e instala os tratadores de erro e o fechamento do banco."""
    for metodo, url, endpoint, funcao in ROTAS:
        app.add_url_rule(url, endpoint, funcao, methods=[metodo])
    app.register_error_handler(413, upload_grande)                 # upload acima do limite do servidor
    app.register_error_handler(ErroDeNegocio, resposta_de_erro)    # erro do Model -> 400/401/404/409
    app.teardown_appcontext(fechar_db)                             # fecha a conexão SQLite da requisição
