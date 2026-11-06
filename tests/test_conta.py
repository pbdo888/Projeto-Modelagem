"""
Testes da conta do usuário: cadastro, login, logout, endereço fixo e progresso no mapa de cupons.
Formato AAA: Arrange (preparar), Act (agir) e Assert (conferir).
"""
import math

import openpyxl
import pytest

from conftest import ANA, consultar, dados_cadastro, executar


def test_login_com_usuario_de_exemplo(cliente):
    """ana@exemplo.com / mccrea entra e recebe só os dados públicos (sem o hash da senha)."""
    # Act
    resposta = cliente.post("/api/login", json=ANA)
    # Assert
    assert resposta.status_code == 200
    assert resposta.get_json()["nome"] == "Ana Souza"
    assert "senha_hash" not in resposta.get_json()


def test_login_com_senha_errada(cliente):
    """Senha errada responde 401 com a mensagem da tela de login."""
    # Act
    resposta = cliente.post("/api/login", json={"email": "ana@exemplo.com", "senha": "errada"})
    # Assert
    assert resposta.status_code == 401
    assert resposta.get_json() == {"erro": "e-mail ou senha incorretos"}


def test_login_de_conta_antiga_pede_para_completar_o_cadastro(cliente):
    """Conta antiga (só e-mail, sem senha) recebe 409 e o aviso para finalizar o cadastro."""
    # Arrange
    executar("INSERT INTO usuarios (nome, email) VALUES ('Conta Antiga', 'antiga@exemplo.com')")
    # Act
    resposta = cliente.post("/api/login", json={"email": "antiga@exemplo.com", "senha": "qualquer"})
    # Assert
    assert resposta.status_code == 409
    assert resposta.get_json() == {"erro": "conta antiga: finalize seu cadastro para criar uma senha"}


def test_cadastro_cria_a_conta_ja_logada_e_atualiza_a_planilha(cliente):
    """Cadastro válido: 201, sessão aberta e a pessoa já aparece na planilha de usuários."""
    # Act
    resposta = cliente.post("/api/cadastro", json=dados_cadastro())
    eu = cliente.get("/api/eu")
    # Assert
    assert resposta.status_code == 201
    novo = resposta.get_json()
    assert novo["email"] == "joana@teste.com"
    assert novo["telefone"] == "(11) 91234-5678"
    assert novo["cep"] == "01310-100"
    assert "senha_hash" not in novo
    assert eu.status_code == 200 and eu.get_json()["usuario"]["id"] == novo["id"]
    planilha = openpyxl.load_workbook("planilhas/usuarios.xlsx").active
    assert "joana@teste.com" in [linha[2] for linha in planilha.iter_rows(min_row=2, values_only=True)]


def test_cadastro_com_email_ja_usado(cliente):
    """E-mail que já tem senha responde 409."""
    # Act
    resposta = cliente.post("/api/cadastro", json=dados_cadastro(email="ana@exemplo.com"))
    # Assert
    assert resposta.status_code == 409
    assert resposta.get_json() == {"erro": "este e-mail já tem cadastro; use Entrar"}


@pytest.mark.parametrize("trocas, mensagem", [
    ({"email": "sem-arroba"}, "e-mail inválido"),
    ({"senha": "123"}, "a senha precisa ter pelo menos 6 caracteres"),
    ({"nascimento": "10/05/2000"}, "data de nascimento inválida"),
    ({"nascimento": "2020-01-01"}, "é preciso ter pelo menos 13 anos para se cadastrar"),
    ({"telefone": "1234"}, "telefone inválido (DDD + número)"),
    ({"moradores": "muitos"}, "informe quantas pessoas moram na sua casa"),
    ({"moradores": 0}, "número de moradores inválido"),
    ({"como_conheceu": "TV"}, "opção inválida em 'como conheceu'"),
    ({"aceite_termos": False}, "é preciso aceitar os termos de uso e a política de privacidade"),
    ({"nome": ""}, "informe o nome completo"),
    ({"sexo": "X"}, "escolha o sexo"),
    ({"estado_civil": "X"}, "escolha o estado civil"),
    ({"cep": "123"}, "CEP inválido (8 dígitos)"),
    ({"lat": None}, "localize o endereço no mapa antes de continuar"),
    ({"lat": 95}, "coordenadas inválidas"),
    ({"numero": "12345678901"}, "o número muito longo"),
    ({"uf": "XX"}, "escolha o estado (UF)"),
])
def test_cadastro_invalido_explica_o_erro(cliente, trocas, mensagem):
    """Cada regra do cadastro devolve 400 com a mensagem que aparece na tela."""
    # Act
    resposta = cliente.post("/api/cadastro", json=dados_cadastro(**trocas))
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": mensagem}


def test_cadastro_completa_conta_antiga_e_mantem_os_pontos(cliente):
    """Conta antiga com o mesmo e-mail é completada (não duplicada) e mantém os pontos."""
    # Arrange
    executar("INSERT INTO usuarios (nome, email, pontos) VALUES ('Conta Antiga', 'antiga@exemplo.com', 50)")
    # Act
    resposta = cliente.post("/api/cadastro", json=dados_cadastro(email="antiga@exemplo.com"))
    # Assert
    assert resposta.status_code == 201
    assert resposta.get_json()["pontos"] == 50
    assert resposta.get_json()["nome"] == "Joana Teste"
    assert len(consultar("SELECT id FROM usuarios WHERE email = 'antiga@exemplo.com'")) == 1


def test_progresso_exige_login(cliente):
    """Sem sessão, /api/eu responde 401."""
    # Act
    resposta = cliente.get("/api/eu")
    # Assert
    assert resposta.status_code == 401
    assert resposta.get_json() == {"erro": "faça login para continuar"}


def test_progresso_libera_fases_pelos_pontos_acumulados(cliente_logado):
    """Cada cupom ativo é uma fase; ela libera quando os pontos acumulados alcançam o custo."""
    # Arrange
    acumulados = consultar("SELECT SUM(pontos) AS t FROM depositos WHERE usuario_id = 1")[0]["t"]
    # Act
    dados = cliente_logado.get("/api/eu").get_json()
    # Assert
    custos = [f["custo"] for f in dados["fases"]]
    proximo = next((c for c in custos if c > acumulados), None)
    assert dados["pontos_totais"] == acumulados
    assert custos == [100, 250, 400, 600, 900, 1500]
    assert dados["fase_atual"] == sum(c <= acumulados for c in custos)
    assert dados["faltam_pontos"] == (proximo - acumulados if proximo else 0)
    assert dados["faltam_itens"] == math.ceil(dados["faltam_pontos"] / 10)
    assert "senha_hash" not in dados["usuario"]


def test_mudar_endereco_troca_o_endereco_fixo(cliente_logado):
    """Novo endereço válido é gravado e aparece no progresso."""
    # Arrange
    novo = {"cep": "05422-010", "logradouro": "Rua dos Pinheiros", "numero": "500", "complemento": "",
            "bairro": "Pinheiros", "cidade": "São Paulo", "uf": "SP", "lat": -23.5670, "lng": -46.6900}
    # Act
    resposta = cliente_logado.post("/api/eu/endereco", json=novo)
    # Assert
    assert resposta.status_code == 200
    assert resposta.get_json() == {"ok": True}
    assert cliente_logado.get("/api/eu").get_json()["usuario"]["bairro"] == "Pinheiros"


def test_mudar_endereco_com_cep_invalido(cliente_logado):
    """Endereço inválido responde 400 e não muda nada."""
    # Act
    resposta = cliente_logado.post("/api/eu/endereco", json={"cep": "1"})
    # Assert
    assert resposta.status_code == 400
    assert resposta.get_json() == {"erro": "CEP inválido (8 dígitos)"}


def test_logout_encerra_a_sessao(cliente_logado):
    """Depois do logout, as rotas de usuário voltam a pedir login."""
    # Act
    resposta = cliente_logado.post("/api/logout")
    # Assert
    assert resposta.get_json() == {"ok": True}
    assert cliente_logado.get("/api/eu").status_code == 401
