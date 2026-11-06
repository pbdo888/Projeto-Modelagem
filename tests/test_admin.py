"""
Testes da área do administrador: planilha de usuários e análise por localização.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import io

import openpyxl

from conftest import ADMIN, consultar


def test_planilha_baixa_com_todos_os_usuarios(cliente):
    """A planilha vem como anexo, sem cache, com o cabeçalho e uma linha por usuário."""
    # Act
    resposta = cliente.get("/api/admin/planilha", headers=ADMIN)
    conteudo = resposta.data
    resposta.close()
    # Assert
    assert resposta.status_code == 200
    assert "attachment" in resposta.headers["Content-Disposition"]
    assert "usuarios_mccrea.xlsx" in resposta.headers["Content-Disposition"]
    assert resposta.headers["Cache-Control"] == "no-store"
    linhas = list(openpyxl.load_workbook(io.BytesIO(conteudo)).active.iter_rows(values_only=True))
    assert linhas[0][:3] == ("ID", "Nome", "E-mail")
    assert len(linhas) == 1 + 8


def test_planilha_exige_token(cliente):
    """Planilha tem dados pessoais (LGPD): só com o token."""
    # Act
    resposta = cliente.get("/api/admin/planilha")
    # Assert
    assert resposta.status_code == 401


def test_analise_por_bairro_e_material(cliente):
    """Os totais por bairro e por material batem com os depósitos do banco."""
    # Arrange
    total_itens = consultar("SELECT SUM(quantidade) AS t FROM depositos")[0]["t"]
    # Act
    dados = cliente.get("/api/analise", headers=ADMIN).get_json()
    # Assert
    assert len(dados["por_bairro"]) == 10
    assert {m["material"] for m in dados["por_material"]} == {"pet", "lata", "vidro", "papel"}
    assert sum(b["itens"] for b in dados["por_bairro"]) == total_itens
    assert sum(m["itens"] for m in dados["por_material"]) == total_itens


def test_analise_exige_token(cliente):
    """Análise só para o admin."""
    # Act
    resposta = cliente.get("/api/analise")
    # Assert
    assert resposta.status_code == 401
