"""
Testes das páginas (Views) e dos arquivos estáticos: o que o navegador recebe.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
from conftest import ADMIN, baixar


def test_home_mostra_a_casa_com_os_links_do_app(cliente):
    """GET / devolve a Home; os url_for('index') e url_for('app_principal') da View continuam funcionando."""
    # Act
    resposta = cliente.get("/")
    # Assert
    assert resposta.status_code == 200
    assert resposta.mimetype == "text/html"
    assert 'href="/" aria-label="McCrea, início"' in resposta.text
    assert 'href="/app#/entrar"' in resposta.text
    assert 'href="/app#/cadastro"' in resposta.text


def test_app_monta_as_listas_do_cadastro(cliente):
    """GET /app devolve o app completo, com os <select> do cadastro preenchidos pelo servidor."""
    # Act
    resposta = cliente.get("/app")
    # Assert
    assert resposta.status_code == 200
    assert "<option>Prefiro não informar</option>" in resposta.text
    assert "<option>União estável</option>" in resposta.text
    assert "<option>Vi uma máquina na rua</option>" in resposta.text
    assert "<option>SP</option>" in resposta.text
    assert 'href="/static/css/mccrea.css"' in resposta.text
    assert 'src="/static/js/app.js"' in resposta.text


def test_arquivos_estaticos_continuam_em_static(cliente):
    """CSS, JS e cartazes iniciais continuam servidos em /static/."""
    # Act
    css, _ = baixar(cliente, "/static/css/mccrea.css")
    js, _ = baixar(cliente, "/static/js/app.js")
    cartaz, imagem = baixar(cliente, "/static/cartazes/mccrea-01.png")
    # Assert
    assert css == js == cartaz == 200
    assert imagem.startswith(b"\x89PNG")


def test_painel_admin_exige_o_token(cliente):
    """Sem o X-Admin-Token certo, o HTML do painel não sai do servidor."""
    # Act
    sem_token = cliente.get("/api/admin/painel")
    token_errado = cliente.get("/api/admin/painel", headers={"X-Admin-Token": "chute"})
    # Assert
    assert sem_token.status_code == token_errado.status_code == 401
    assert sem_token.get_json() == {"erro": "acesso restrito a administradores"}


def test_painel_admin_com_token_mostra_materiais_e_limite(cliente):
    """Com o token, o painel vem com os pontos por material e o limite de imagem, sem cache."""
    # Act
    resposta = cliente.get("/api/admin/painel", headers=ADMIN)
    # Assert
    assert resposta.status_code == 200
    assert resposta.headers["Cache-Control"] == "no-store"
    assert "PET (10 pontos por item)" in resposta.text
    assert "LATA (15 pontos por item)" in resposta.text
    assert "até 5 MB" in resposta.text


def test_rota_inexistente_devolve_404(cliente):
    """Endereço que não existe continua dando 404 (os templates não ficam expostos)."""
    # Act
    resposta = cliente.get("/templates/casa.html")
    # Assert
    assert resposta.status_code == 404
