"""
Testes dos cupons: lista pública, criação pelo admin e resgate com pontos.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import re

import pytest

from conftest import ADMIN, consultar, executar


def test_lista_cupons_ativos_do_mais_barato_ao_mais_caro(cliente):
    """Cupom desativado não aparece; os ativos vêm em ordem de custo."""
    # Arrange
    executar("INSERT INTO cupons (marca, descricao, custo, ativo) VALUES ('Oculta', 'x', 50, 0)")
    # Act
    cupons = cliente.get("/api/cupons").get_json()
    # Assert
    assert [c["custo"] for c in cupons] == [100, 250, 400, 600, 900, 1500]


def test_resgate_desconta_pontos_e_gera_codigo(cliente_logado):
    """Resgatar o cupom de 100 pontos gera um código de 8 caracteres e desconta o saldo."""
    # Arrange
    antes = consultar("SELECT pontos FROM usuarios WHERE id = 1")[0]["pontos"]
    # Act
    resposta = cliente_logado.post("/api/resgatar", json={"cupom_id": 1})
    # Assert
    assert resposta.status_code == 200
    codigo = resposta.get_json()["codigo"]
    assert re.fullmatch(r"[0-9A-F]{8}", codigo)
    assert consultar("SELECT pontos FROM usuarios WHERE id = 1")[0]["pontos"] == antes - 100
    assert consultar("SELECT codigo FROM resgates")[0]["codigo"] == codigo


def test_resgate_sem_pontos_suficientes(cliente_logado):
    """Saldo menor que o custo: 409 e nada é descontado."""
    # Arrange
    executar("UPDATE usuarios SET pontos = 10 WHERE id = 1")
    # Act
    resposta = cliente_logado.post("/api/resgatar", json={"cupom_id": 1})
    # Assert
    assert resposta.status_code == 409
    assert resposta.get_json() == {"erro": "pontos insuficientes"}
    assert consultar("SELECT pontos FROM usuarios WHERE id = 1")[0]["pontos"] == 10


@pytest.mark.parametrize("dados, status, mensagem", [
    ({}, 400, "dados inválidos"),
    ({"cupom_id": "abc"}, 400, "dados inválidos"),
    ({"cupom_id": 999}, 404, "cupom não encontrado"),
])
def test_resgate_invalido(cliente_logado, dados, status, mensagem):
    """Cupom ausente, inválido ou inexistente."""
    # Act
    resposta = cliente_logado.post("/api/resgatar", json=dados)
    # Assert
    assert resposta.status_code == status
    assert resposta.get_json() == {"erro": mensagem}


def test_resgate_exige_login(cliente):
    """Sem sessão não há resgate."""
    # Act
    resposta = cliente.post("/api/resgatar", json={"cupom_id": 1})
    # Assert
    assert resposta.status_code == 401
    assert resposta.get_json() == {"erro": "faça login para continuar"}


def test_criar_cupom(cliente):
    """O admin cria um cupom e ele entra na lista pública."""
    # Act
    resposta = cliente.post("/api/cupons", json={"marca": "Padaria Sol", "descricao": "Pão grátis", "custo": 150},
                            headers=ADMIN)
    # Assert
    assert resposta.status_code == 201
    assert "Padaria Sol" in [c["marca"] for c in cliente.get("/api/cupons").get_json()]


@pytest.mark.parametrize("dados, mensagem", [
    ({}, "informe marca, descricao e custo"),
    ({"marca": "A", "descricao": "B", "custo": 0}, "dados inválidos"),
    ({"marca": " ", "descricao": "B", "custo": 10}, "dados inválidos"),
])
def test_criar_cupom_invalido(cliente, dados, mensagem):
    """Cupom sem os campos ou com custo menor que 1: 400."""
    # Act
    resposta = cliente.post("/api/cupons", json=dados, headers=ADMIN)
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": mensagem}
