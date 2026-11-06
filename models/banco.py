"""
Banco de dados (SQLite): conexão por requisição, esquema das tabelas, migração e criação inicial.

A conexão da requisição fica guardada em `flask.g`: abre na primeira consulta e fecha no
fim da requisição (fechar_db, registrado pelo controllers/__init__.py).
"""
import sqlite3

from flask import g

from models import dados_exemplo

DB_PATH = "mccrea.db"  # relativo à pasta de onde o app roda (a raiz do projeto)

# Colunas do cadastro completo. Entram por ALTER TABLE para que bancos antigos sejam
# atualizados sem perder dados.
COLUNAS_CADASTRO = {
    "senha_hash": "TEXT", "nascimento": "TEXT", "sexo": "TEXT", "estado_civil": "TEXT",
    "telefone": "TEXT", "moradores": "INTEGER", "como_conheceu": "TEXT",
    "aceita_ofertas": "INTEGER NOT NULL DEFAULT 0", "aceite_termos_em": "TEXT",
    "cep": "TEXT", "logradouro": "TEXT", "numero": "TEXT", "complemento": "TEXT",
    "bairro": "TEXT", "cidade": "TEXT", "uf": "TEXT", "lat": "REAL", "lng": "REAL",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  pontos INTEGER NOT NULL DEFAULT 0,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS funcionarios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  cargo TEXT NOT NULL CHECK (cargo IN ('coletador', 'tecnico', 'admin')),
  telefone TEXT
);
CREATE TABLE IF NOT EXISTS maquinas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  endereco TEXT,
  bairro TEXT,
  lat REAL NOT NULL,
  lng REAL NOT NULL,
  capacidade INTEGER NOT NULL DEFAULT 500,
  ocupacao INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'ativa' CHECK (status IN ('ativa', 'manutencao', 'inativa')),
  criada_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cupons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  marca TEXT NOT NULL,
  descricao TEXT NOT NULL,
  custo INTEGER NOT NULL CHECK (custo > 0),
  ativo INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS depositos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
  maquina_id INTEGER NOT NULL REFERENCES maquinas(id),
  material TEXT NOT NULL,
  quantidade INTEGER NOT NULL,
  pontos INTEGER NOT NULL,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS resgates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
  cupom_id INTEGER NOT NULL REFERENCES cupons(id),
  codigo TEXT NOT NULL UNIQUE,
  pontos INTEGER NOT NULL,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS coletas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  funcionario_id INTEGER NOT NULL REFERENCES funcionarios(id),
  maquina_id INTEGER NOT NULL REFERENCES maquinas(id),
  itens INTEGER NOT NULL,
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS anuncios (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  titulo TEXT NOT NULL,
  texto TEXT NOT NULL,
  imagem TEXT NOT NULL,  -- caminho público do cartaz (/static/cartazes/... ou /uploads/anuncios/...)
  ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
  ordem INTEGER NOT NULL DEFAULT 0,  -- menor aparece antes no carrossel
  criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


def get_db():
    """Conexão SQLite da requisição atual (abre na primeira chamada, com as chaves estrangeiras ligadas)."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def fechar_db(_):
    """Fecha a conexão no fim da requisição."""
    con = g.pop("db", None)
    if con is not None:
        con.close()


def rows(sql, args=()):
    """Todas as linhas da consulta, como dicionários."""
    return [dict(r) for r in get_db().execute(sql, args)]


def one(sql, args=()):
    """A primeira linha da consulta como dicionário, ou None."""
    r = get_db().execute(sql, args).fetchone()
    return dict(r) if r else None


def migrar(con):
    """Acrescenta as colunas de cadastro que faltarem (bancos antigos não perdem dados)."""
    existentes = {r[1] for r in con.execute("PRAGMA table_info(usuarios)")}
    for col, tipo in COLUNAS_CADASTRO.items():
        if col not in existentes:
            con.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipo}")


def init_db():
    """Cria as tabelas que faltam, põe os dados de exemplo num banco novo e aplica a migração."""
    con = sqlite3.connect(DB_PATH)
    # Os cartazes iniciais entram só quando a tabela é criada; se o admin excluir todos, não voltam.
    sem_anuncios = not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'anuncios'").fetchone()
    con.executescript(SCHEMA)
    if con.execute("SELECT COUNT(*) FROM maquinas").fetchone()[0] == 0:
        dados_exemplo.seed(con)
    if sem_anuncios:
        dados_exemplo.seed_anuncios(con)
    migrar(con)
    dados_exemplo.completar_perfis_demo(con)
    con.commit()
    con.close()
