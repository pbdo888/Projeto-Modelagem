"""Banco de dados (SQLite): esquema e dados de exemplo para análise por localização."""
import math
import random
import sqlite3
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

DB_PATH = "reciclaverde.db"
FMT = "%Y-%m-%d %H:%M:%S"
PONTOS_MATERIAL = {"pet": 10, "lata": 15, "vidro": 20, "papel": 5}  # pontos por item
PONTOS_ITEM_MEDIO = 10  # só para estimar "faltam N itens"
SENHA_DEMO = "reciclaverde"  # senha dos usuários de exemplo (@exemplo.com)

# Colunas do cadastro completo. Entram por ALTER TABLE para que bancos antigos sejam
# atualizados sem perder dados.
COLUNAS_CADASTRO = {
    "senha_hash": "TEXT", "nascimento": "TEXT", "sexo": "TEXT", "estado_civil": "TEXT",
    "telefone": "TEXT", "moradores": "INTEGER", "como_conheceu": "TEXT",
    "aceita_ofertas": "INTEGER NOT NULL DEFAULT 0", "aceite_termos_em": "TEXT",
    "cep": "TEXT", "logradouro": "TEXT", "numero": "TEXT", "complemento": "TEXT",
    "bairro": "TEXT", "cidade": "TEXT", "uf": "TEXT", "lat": "REAL", "lng": "REAL",
}

# Perfis dos usuários de exemplo: (nascimento, sexo, estado civil, moradores, logradouro, número, bairro, CEP, lat, lng)
PERFIS_DEMO = {
    "ana@exemplo.com": ("1994-03-12", "Feminino", "Solteiro(a)", 2, "Rua Augusta", "1200", "Consolação", "01304-001", -23.5571, -46.6588),
    "bruno@exemplo.com": ("1988-07-30", "Masculino", "Casado(a)", 4, "Rua Teodoro Sampaio", "800", "Pinheiros", "05406-050", -23.5590, -46.6820),
    "carla@exemplo.com": ("2001-11-05", "Feminino", "Solteiro(a)", 3, "Rua da Mooca", "2500", "Mooca", "03104-002", -23.5560, -46.6050),
    "diego@exemplo.com": ("1979-01-22", "Masculino", "Divorciado(a)", 1, "Avenida Cruzeiro do Sul", "1800", "Santana", "02031-000", -23.5080, -46.6260),
    "elisa@exemplo.com": ("1996-05-18", "Feminino", "União estável", 2, "Rua Harmonia", "300", "Vila Madalena", "05435-000", -23.5530, -46.6880),
    "felipe@exemplo.com": ("1985-09-09", "Masculino", "Casado(a)", 5, "Rua Tuiuti", "1500", "Tatuapé", "03081-000", -23.5420, -46.5780),
    "gabi@exemplo.com": ("2003-02-14", "Outro", "Solteiro(a)", 4, "Rua Clélia", "900", "Lapa", "05042-000", -23.5260, -46.6960),
    "hugo@exemplo.com": ("1970-12-01", "Masculino", "Viúvo(a)", 1, "Avenida Adolfo Pinheiro", "700", "Santo Amaro", "04734-001", -23.6480, -46.7030),
}


def dist_km(lat1, lng1, lat2, lng2):
    """Distância euclidiana no plano (lat, lng). Graus viram km: 1° ≈ 111,32 km,
    e a longitude é encolhida por cos(latitude) para não distorcer o resultado."""
    x = (lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = lat2 - lat1
    return 111.32 * math.hypot(x, y)

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
"""


def seed(con):
    rnd = random.Random(7)  # reprodutível
    maquinas = [  # (nome, bairro, lat, lng): locais de exemplo em São Paulo
        ("EcoPonto Paulista", "Bela Vista", -23.5614, -46.6559),
        ("EcoPonto Ibirapuera", "Ibirapuera", -23.5874, -46.6576),
        ("EcoPonto Sé", "Sé", -23.5505, -46.6333),
        ("EcoPonto Largo da Batata", "Pinheiros", -23.5670, -46.6917),
        ("EcoPonto Vila Madalena", "Vila Madalena", -23.5546, -46.6918),
        ("EcoPonto Mooca", "Mooca", -23.5599, -46.5987),
        ("EcoPonto Santana", "Santana", -23.5025, -46.6290),
        ("EcoPonto Tatuapé", "Tatuapé", -23.5400, -46.5760),
        ("EcoPonto Santo Amaro", "Santo Amaro", -23.6540, -46.7090),
        ("EcoPonto Lapa", "Lapa", -23.5230, -46.7020),
    ]
    con.executemany(
        "INSERT INTO maquinas (nome, endereco, bairro, lat, lng, ocupacao) VALUES (?,?,?,?,?,?)",
        [(n, f"{b}, São Paulo - SP", b, la, lo, rnd.randint(40, 380)) for n, b, la, lo in maquinas])
    con.executemany("INSERT INTO usuarios (nome, email) VALUES (?,?)", [
        (n, f"{n.split()[0].lower()}@exemplo.com") for n in
        ["Ana Souza", "Bruno Lima", "Carla Dias", "Diego Alves",
         "Elisa Rocha", "Felipe Costa", "Gabi Nunes", "Hugo Pires"]])
    con.executemany("INSERT INTO funcionarios (nome, cargo, telefone) VALUES (?,?,?)", [
        ("Marcos Silva", "coletador", "(11) 90000-0001"),
        ("Paula Reis", "coletador", "(11) 90000-0002"),
        ("Rafael Moura", "tecnico", "(11) 90000-0003"),
        ("Sônia Prado", "admin", None)])
    con.executemany("INSERT INTO cupons (marca, descricao, custo) VALUES (?,?,?)", [
        ("Café Verde", "10% de desconto no café", 100),
        ("Cinema Mais", "Ingresso 2x1", 250),
        ("Mercado Bom Preço", "R$ 10 de desconto", 400),
        ("Bike Sampa", "1 dia de bike grátis", 600),
        ("Livraria Folha", "20% em livros", 900),
        ("Pizzaria Forno", "Pizza média grátis", 1500)])

    agora = datetime.now()
    for _ in range(150):  # depósitos dos últimos 90 dias; uns usuários/máquinas mais ativos que outros
        u = rnd.choices(range(1, 9), [30, 20, 15, 12, 8, 6, 5, 4])[0]
        m = rnd.choices(range(1, 11), [5, 3, 4, 3, 2, 3, 2, 3, 1, 2])[0]
        mat, qtd = rnd.choice(list(PONTOS_MATERIAL)), rnd.randint(1, 4)
        pts = qtd * PONTOS_MATERIAL[mat]
        quando = agora - timedelta(days=rnd.randint(0, 90), minutes=rnd.randint(0, 1439))
        con.execute(
            "INSERT INTO depositos (usuario_id, maquina_id, material, quantidade, pontos, criado_em) "
            "VALUES (?,?,?,?,?,?)", (u, m, mat, qtd, pts, quando.strftime(FMT)))
        con.execute("UPDATE usuarios SET pontos = pontos + ? WHERE id = ?", (pts, u))
    for _ in range(12):  # coletas feitas pelos coletadores
        quando = agora - timedelta(days=rnd.randint(0, 90))
        con.execute(
            "INSERT INTO coletas (funcionario_id, maquina_id, itens, criado_em) VALUES (?,?,?,?)",
            (rnd.randint(1, 2), rnd.randint(1, 10), rnd.randint(80, 300), quando.strftime(FMT)))


def migrar(con):
    """Acrescenta as colunas de cadastro que faltarem e completa os usuários de exemplo."""
    existentes = {r[1] for r in con.execute("PRAGMA table_info(usuarios)")}
    for col, tipo in COLUNAS_CADASTRO.items():
        if col not in existentes:
            con.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipo}")
    senha = generate_password_hash(SENHA_DEMO)
    for email, (nasc, sexo, ec, mor, logr, num, bairro, cep, lat, lng) in PERFIS_DEMO.items():
        con.execute(
            "UPDATE usuarios SET senha_hash=?, nascimento=?, sexo=?, estado_civil=?, moradores=?, "
            "telefone='(11) 99999-0000', logradouro=?, numero=?, bairro=?, cidade='São Paulo', uf='SP', "
            "cep=?, lat=?, lng=?, aceite_termos_em=criado_em WHERE email=? AND senha_hash IS NULL",
            (senha, nasc, sexo, ec, mor, logr, num, bairro, cep, lat, lng, email))


def init_db():
    con = sqlite3.connect(DB_PATH)
    con.executescript(SCHEMA)
    if con.execute("SELECT COUNT(*) FROM maquinas").fetchone()[0] == 0:
        seed(con)
    migrar(con)
    con.commit()
    con.close()
