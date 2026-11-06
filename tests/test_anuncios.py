"""
Testes das notícias (anúncios com cartaz): carrossel público e gestão pelo admin.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import io

import pytest

from conftest import ADMIN, baixar, png_minimo

MULTIPART = "multipart/form-data"


def _com_cartaz(campos, conteudo=None, nome="cartaz.png"):
    """Formulário do admin; com `conteudo`, vai junto um arquivo no campo imagem."""
    dados = dict(campos)
    if conteudo is not None:
        dados["imagem"] = (io.BytesIO(conteudo), nome)
    return dados


def test_lista_os_13_cartazes_iniciais(cliente):
    """O carrossel começa com os 13 slides da apresentação, na ordem."""
    # Act
    anuncios = cliente.get("/api/anuncios").get_json()
    # Assert
    assert len(anuncios) == 13
    assert anuncios[0]["titulo"] == "McCrea: reciclar vira desconto"
    assert anuncios[0]["imagem"] == "/static/cartazes/mccrea-01.png"
    assert set(anuncios[0]) == {"id", "titulo", "texto", "imagem", "criado_em"}


def test_ver_um_anuncio(cliente):
    """GET /api/anuncios/<id> traz o anúncio completo ("Saiba mais")."""
    # Act
    anuncio = cliente.get("/api/anuncios/2").get_json()
    # Assert
    assert anuncio["titulo"] == "O Brasil gera muito e recicla pouco"
    assert "Abrema" in anuncio["texto"]


def test_ver_anuncio_inexistente(cliente):
    """Anúncio que não existe: 404."""
    # Act
    resposta = cliente.get("/api/anuncios/999")
    # Assert
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "anúncio não encontrado"}


def test_criar_editar_e_excluir_anuncio_com_cartaz(cliente):
    """Ciclo completo: o cartaz enviado é servido, trocado (o antigo some) e apagado com o anúncio."""
    # Arrange
    png = png_minimo()
    # Act 1: criar
    criado = cliente.post("/api/anuncios", headers=ADMIN, content_type=MULTIPART,
                          data=_com_cartaz({"titulo": "Mutirão", "texto": "Sábado de manhã"}, png))
    # Assert 1
    assert criado.status_code == 201
    anuncio = criado.get_json()
    assert anuncio["imagem"].startswith("/uploads/anuncios/") and anuncio["imagem"].endswith(".png")
    assert baixar(cliente, anuncio["imagem"]) == (200, png)
    # Act 2: editar trocando o cartaz
    editado = cliente.put(f"/api/anuncios/{anuncio['id']}", headers=ADMIN, content_type=MULTIPART,
                          data=_com_cartaz({"titulo": "Mutirão de sábado", "texto": "Das 9h às 12h"}, png, "novo.png"))
    # Assert 2
    assert editado.status_code == 200
    novo = editado.get_json()
    assert novo["titulo"] == "Mutirão de sábado" and novo["imagem"] != anuncio["imagem"]
    assert baixar(cliente, anuncio["imagem"])[0] == 404
    # Act 3: excluir
    excluido = cliente.delete(f"/api/anuncios/{anuncio['id']}", headers=ADMIN)
    # Assert 3
    assert excluido.get_json() == {"ok": True}
    assert cliente.get(f"/api/anuncios/{anuncio['id']}").status_code == 404
    assert baixar(cliente, novo["imagem"])[0] == 404


def test_editar_sem_cartaz_novo_mantem_a_imagem(cliente):
    """Editar só o texto mantém o cartaz inicial (que fica em /static e nunca é apagado)."""
    # Act
    resposta = cliente.put("/api/anuncios/1", headers=ADMIN, content_type=MULTIPART,
                           data={"titulo": "Título novo", "texto": "Texto novo", "ordem": "1"})
    # Assert
    assert resposta.status_code == 200
    assert resposta.get_json()["imagem"] == "/static/cartazes/mccrea-01.png"
    assert resposta.get_json()["titulo"] == "Título novo"


@pytest.mark.parametrize("campos, mensagem", [
    ({"texto": "x"}, "informe o título"),
    ({"titulo": "AB", "texto": "x"}, "o título precisa ter pelo menos 3 caracteres"),
    ({"titulo": "Título", "texto": "x", "ordem": "abc"}, "ordem inválida"),
    ({"titulo": "Título", "texto": "x", "ordem": "10000"}, "a ordem deve ficar entre 0 e 9999"),
    ({"titulo": "Título"}, "informe o texto do anúncio"),
    ({"titulo": "Título", "texto": "x"}, "envie a imagem do cartaz"),
])
def test_criar_anuncio_invalido(cliente, campos, mensagem):
    """Cada regra do formulário de anúncio devolve 400 com a mensagem do painel."""
    # Act
    resposta = cliente.post("/api/anuncios", headers=ADMIN, content_type=MULTIPART, data=campos)
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": mensagem}


def test_cartaz_que_nao_e_imagem(cliente):
    """O formato é conferido pelo conteúdo do arquivo (SVG e texto são recusados)."""
    # Act
    resposta = cliente.post("/api/anuncios", headers=ADMIN, content_type=MULTIPART,
                            data=_com_cartaz({"titulo": "Título", "texto": "x"}, b"<svg></svg>", "a.svg"))
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": "formato de imagem inválido (use PNG, JPG, WebP ou GIF)"}


def test_cartaz_entre_5_e_6_mb_e_recusado(cliente):
    """Imagem acima de 5 MB (mas dentro do limite do servidor) é recusada com 400."""
    # Arrange
    grande = png_minimo() + b"0" * int(5.5 * 1024 * 1024)
    # Act
    resposta = cliente.post("/api/anuncios", headers=ADMIN, content_type=MULTIPART,
                            data=_com_cartaz({"titulo": "Título", "texto": "x"}, grande))
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": "imagem muito grande (máximo 5 MB)"}


def test_envio_acima_do_limite_do_servidor_devolve_413(cliente):
    """Requisição maior que o limite do Flask (6 MB) responde 413 em JSON."""
    # Arrange
    enorme = png_minimo() + b"0" * (7 * 1024 * 1024)
    # Act
    resposta = cliente.post("/api/anuncios", headers=ADMIN, content_type=MULTIPART,
                            data=_com_cartaz({"titulo": "Título", "texto": "x"}, enorme))
    # Assert
    assert resposta.status_code == 413
    assert resposta.get_json() == {"erro": "imagem muito grande (máximo 5 MB)"}


def test_anuncio_oculto_so_aparece_para_o_admin(cliente):
    """ativo=0: some do carrossel, mas continua na lista do admin."""
    # Arrange
    criado = cliente.post("/api/anuncios", headers=ADMIN, content_type=MULTIPART,
                          data=_com_cartaz({"titulo": "Rascunho", "texto": "x", "ativo": "0"}, png_minimo()))
    aid = criado.get_json()["id"]
    # Act
    publicos = [a["id"] for a in cliente.get("/api/anuncios").get_json()]
    do_admin = [a["id"] for a in cliente.get("/api/admin/anuncios", headers=ADMIN).get_json()]
    # Assert
    assert aid not in publicos
    assert aid in do_admin
    assert cliente.get(f"/api/anuncios/{aid}").status_code == 404


def test_editar_ou_excluir_anuncio_inexistente(cliente):
    """PUT e DELETE de anúncio que não existe: 404 (sem cache, como toda resposta de admin)."""
    # Act
    editar = cliente.put("/api/anuncios/999", headers=ADMIN, content_type=MULTIPART, data={"titulo": "Título"})
    excluir = cliente.delete("/api/anuncios/999", headers=ADMIN)
    # Assert
    assert editar.status_code == excluir.status_code == 404
    assert editar.get_json() == excluir.get_json() == {"erro": "anúncio não encontrado"}
    assert editar.headers["Cache-Control"] == excluir.headers["Cache-Control"] == "no-store"


def test_gestao_de_anuncios_exige_token(cliente):
    """Criar, editar, excluir e listar todos: só com o token de admin."""
    # Act
    respostas = [
        cliente.post("/api/anuncios", content_type=MULTIPART, data={"titulo": "Título"}),
        cliente.put("/api/anuncios/1", content_type=MULTIPART, data={"titulo": "Título"}),
        cliente.delete("/api/anuncios/1"),
        cliente.get("/api/admin/anuncios"),
    ]
    # Assert
    assert [r.status_code for r in respostas] == [401, 401, 401, 401]
