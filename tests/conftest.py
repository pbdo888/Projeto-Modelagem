"""
Preparação dos testes (fixtures do pytest).

Cada teste roda numa pasta temporária NOVA e o app é importado lá dentro: mccrea.db,
planilhas/ e uploads/ nascem nessa pasta, já com os dados de exemplo (ana@exemplo.com /
mccrea etc.). O banco de verdade do projeto nunca é tocado.

O app é sempre importado do zero pelo app.py da raiz, do mesmo jeito que o `python app.py`
e o `gunicorn app:app` fazem. Por isso estes testes não dependem da organização interna do
código: foram escritos ANTES da refatoração para MVC e continuam valendo depois dela.
"""
import importlib
import sqlite3
import struct
import sys
import zlib
from pathlib import Path

import pytest

PASTA_PROJETO = Path(__file__).resolve().parent.parent
TOKEN_TESTE = "token-de-teste"
ADMIN = {"X-Admin-Token": TOKEN_TESTE}
ANA = {"email": "ana@exemplo.com", "senha": "mccrea"}


def _esquecer_modulos_do_projeto():
    """Tira do cache de imports os módulos do projeto (menos .venv e tests) para o app nascer de novo."""
    for nome, modulo in list(sys.modules.items()):
        arquivo = getattr(modulo, "__file__", None)
        if not arquivo:
            continue
        try:
            partes = Path(arquivo).resolve().relative_to(PASTA_PROJETO).parts
        except ValueError:
            continue  # módulo de fora do projeto (Flask, biblioteca padrão...)
        if partes[0] not in (".venv", "tests"):
            del sys.modules[nome]


@pytest.fixture
def app(tmp_path, monkeypatch):
    """App Flask novo, com banco, planilha e uploads numa pasta temporária."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ADMIN_TOKEN", TOKEN_TESTE)
    monkeypatch.setenv("SECRET_KEY", "chave-de-teste")
    monkeypatch.delenv("RENDER", raising=False)
    _esquecer_modulos_do_projeto()
    modulo = importlib.import_module("app")
    modulo.app.config["TESTING"] = True
    return modulo.app


@pytest.fixture
def cliente(app):
    """Navegador de mentira: faz requisições ao app sem abrir servidor."""
    return app.test_client()


@pytest.fixture
def cliente_logado(cliente):
    """Navegador já logado como a usuária de exemplo Ana Souza."""
    cliente.post("/api/login", json=ANA)
    return cliente


def consultar(sql, args=()):
    """Lê direto do banco do teste (mccrea.db da pasta temporária) para conferir o efeito das rotas."""
    con = sqlite3.connect("mccrea.db")
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, args)]
    finally:
        con.close()


def executar(sql, args=()):
    """Grava direto no banco do teste (para montar situações, como uma conta antiga sem senha)."""
    con = sqlite3.connect("mccrea.db")
    try:
        con.execute(sql, args)
        con.commit()
    finally:
        con.close()


def baixar(cliente, url):
    """GET que já fecha a resposta (no Windows, arquivo aberto não pode ser apagado depois)."""
    resposta = cliente.get(url)
    status, conteudo = resposta.status_code, resposta.data
    resposta.close()
    return status, conteudo


def dados_cadastro(**trocas):
    """JSON de cadastro válido; `trocas` muda só os campos que o teste quer testar."""
    dados = {
        "nome": "Joana Teste", "email": "joana@teste.com", "senha": "segredo1",
        "nascimento": "2000-05-10", "sexo": "Feminino", "estado_civil": "Solteiro(a)",
        "telefone": "11912345678", "moradores": 3, "como_conheceu": "Redes sociais",
        "aceita_ofertas": True, "aceite_termos": True,
        "cep": "01310-100", "logradouro": "Avenida Paulista", "numero": "1000", "complemento": "",
        "bairro": "Bela Vista", "cidade": "São Paulo", "uf": "SP", "lat": -23.5650, "lng": -46.6520,
    }
    dados.update(trocas)
    return dados


def png_minimo():
    """Bytes de uma imagem PNG de 1x1 pixel (para testar o envio de cartazes)."""
    def bloco(tipo, conteudo):
        """Um "chunk" do formato PNG: tamanho + tipo + conteúdo + verificação (CRC)."""
        return struct.pack(">I", len(conteudo)) + tipo + conteudo + struct.pack(">I", zlib.crc32(tipo + conteudo))
    cabecalho = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cabecalho)
            + bloco(b"IDAT", zlib.compress(b"\x00\x2f\xb2\x4c")) + bloco(b"IEND", b""))
