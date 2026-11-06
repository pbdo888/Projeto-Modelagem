"""
Testes das máquinas McCrea: lista pública, máquinas mais próximas e cadastro pelo admin.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import pytest

from conftest import ADMIN, executar


def test_lista_so_as_maquinas_ativas(cliente):
    """Máquina em manutenção sai da lista do mapa."""
    # Arrange
    executar("UPDATE maquinas SET status = 'manutencao' WHERE id = 2")
    # Act
    maquinas = cliente.get("/api/maquinas").get_json()
    # Assert
    assert len(maquinas) == 9
    assert all(m["status"] == "ativa" for m in maquinas)


def test_maquinas_proximas_vem_ordenadas_pela_distancia(cliente):
    """As 3 mais próximas, da mais perto para a mais longe (em km)."""
    # Act
    resposta = cliente.get("/api/maquinas/proximas?lat=-23.5614&lng=-46.6559")
    # Assert
    maquinas = resposta.get_json()
    distancias = [m["distancia_km"] for m in maquinas]
    assert resposta.status_code == 200
    assert len(maquinas) == 3
    assert maquinas[0]["nome"] == "EcoPonto Paulista" and distancias[0] == 0.0
    assert distancias == sorted(distancias)


def test_maquinas_proximas_sem_coordenadas(cliente):
    """lat/lng ausentes ou inválidas respondem 400."""
    # Act
    resposta = cliente.get("/api/maquinas/proximas?lat=abc")
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": "informe lat e lng"}


def test_maquinas_proximas_sem_nenhuma_ativa(cliente):
    """Sem máquina ativa, responde 404."""
    # Arrange
    executar("UPDATE maquinas SET status = 'inativa'")
    # Act
    resposta = cliente.get("/api/maquinas/proximas?lat=-23.5&lng=-46.6")
    # Assert
    assert resposta.status_code == 404
    assert resposta.get_json() == {"erro": "nenhuma máquina ativa"}


def test_criar_maquina_exige_token(cliente):
    """Só o admin cadastra máquinas."""
    # Act
    resposta = cliente.post("/api/maquinas", json={"nome": "Nova", "lat": -23.5, "lng": -46.6})
    # Assert
    assert resposta.status_code == 401


@pytest.mark.parametrize("dados, mensagem", [
    ({}, "informe nome, lat e lng"),
    ({"nome": "Nova", "lat": "abc", "lng": -46.6}, "informe nome, lat e lng"),
    ({"nome": "   ", "lat": -23.5, "lng": -46.6}, "nome ou coordenadas inválidos"),
    ({"nome": "Nova", "lat": 95, "lng": -46.6}, "nome ou coordenadas inválidos"),
])
def test_criar_maquina_com_dados_invalidos(cliente, dados, mensagem):
    """Dados inválidos: 400, e a resposta de admin continua sem cache."""
    # Act
    resposta = cliente.post("/api/maquinas", json=dados, headers=ADMIN)
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": mensagem}
    assert resposta.headers["Cache-Control"] == "no-store"


def test_criar_maquina_aparece_no_mapa(cliente):
    """Máquina nova: 201 com o id, e ela entra na lista pública."""
    # Arrange
    nova = {"nome": "EcoPonto Teste", "endereco": "Rua X, 1", "bairro": "Centro", "lat": -23.544, "lng": -46.639}
    # Act
    resposta = cliente.post("/api/maquinas", json=nova, headers=ADMIN)
    # Assert
    assert resposta.status_code == 201
    assert resposta.get_json()["id"] in [m["id"] for m in cliente.get("/api/maquinas").get_json()]
