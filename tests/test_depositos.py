"""
Testes dos depósitos: a leitura da máquina (simulada pelo admin) que vira pontos.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import pytest

from conftest import ADMIN, consultar


def _ocupacao(maquina_id):
    return consultar("SELECT ocupacao FROM maquinas WHERE id = ?", (maquina_id,))[0]["ocupacao"]


def _pontos(usuario_id):
    return consultar("SELECT pontos FROM usuarios WHERE id = ?", (usuario_id,))[0]["pontos"]


def test_deposito_credita_pontos_e_ocupa_a_maquina(cliente):
    """2 latas = 30 pontos para o usuário e 2 itens a mais na máquina."""
    # Arrange
    pontos_antes, ocupacao_antes = _pontos(1), _ocupacao(1)
    deposito = {"usuario_id": 1, "maquina_id": 1, "quantidade": 2, "material": "lata"}
    # Act
    resposta = cliente.post("/api/depositos", json=deposito, headers=ADMIN)
    # Assert
    assert resposta.status_code == 201
    assert resposta.get_json() == {"pontos": 30}
    assert _pontos(1) == pontos_antes + 30
    assert _ocupacao(1) == ocupacao_antes + 2


def test_deposito_em_maquina_cheia(cliente):
    """Mais itens do que cabem: 409."""
    # Act
    resposta = cliente.post("/api/depositos", headers=ADMIN,
                            json={"usuario_id": 1, "maquina_id": 1, "quantidade": 1000, "material": "pet"})
    # Assert
    assert resposta.status_code == 409
    assert resposta.get_json() == {"erro": "máquina indisponível ou cheia"}


def test_deposito_de_usuario_inexistente_desfaz_a_ocupacao(cliente):
    """Usuário que não existe: 404, e a ocupação da máquina volta ao que era (rollback)."""
    # Arrange
    ocupacao_antes = _ocupacao(1)
    # Act
    resposta = cliente.post("/api/depositos", headers=ADMIN,
                            json={"usuario_id": 999, "maquina_id": 1, "quantidade": 2, "material": "pet"})
    # Assert
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "usuário não encontrado"}
    assert _ocupacao(1) == ocupacao_antes


@pytest.mark.parametrize("dados, mensagem", [
    ({"usuario_id": 1, "maquina_id": 1, "quantidade": 2}, "dados inválidos"),
    ({"usuario_id": "x", "maquina_id": 1, "quantidade": 2, "material": "pet"}, "dados inválidos"),
    ({"usuario_id": 1, "maquina_id": 1, "quantidade": 2, "material": "isopor"}, "material ou quantidade inválidos"),
    ({"usuario_id": 1, "maquina_id": 1, "quantidade": 0, "material": "pet"}, "material ou quantidade inválidos"),
])
def test_deposito_com_dados_invalidos(cliente, dados, mensagem):
    """Dados incompletos, material desconhecido ou quantidade zero: 400."""
    # Act
    resposta = cliente.post("/api/depositos", json=dados, headers=ADMIN)
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": mensagem}


def test_deposito_exige_token(cliente):
    """Só a máquina (ou o admin) registra depósitos."""
    # Act
    resposta = cliente.post("/api/depositos", json={"usuario_id": 1, "maquina_id": 1, "quantidade": 1,
                                                    "material": "pet"})
    # Assert
    assert resposta.status_code == 401
