"""Banco de dados (SQLite): esquema e dados de exemplo para análise por localização."""
import math
import random
import sqlite3
from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

DB_PATH = "mccrea.db"
FMT = "%Y-%m-%d %H:%M:%S"
PONTOS_MATERIAL = {"pet": 10, "lata": 15, "vidro": 20, "papel": 5}  # pontos por item
PONTOS_ITEM_MEDIO = 10  # só para estimar "faltam N itens"
SENHA_DEMO = "mccrea"  # senha dos usuários de exemplo (@exemplo.com)

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

# Cartazes iniciais do carrossel de Notícias: os slides da apresentação McCrea.pptx,
# exportados para static/cartazes/mccrea-NN.png (na mesma ordem).
ANUNCIOS_INICIAIS = [
    ("McCrea: reciclar vira desconto",
     "Máquinas inteligentes pela cidade, pontos por item reciclado e cupons de marcas parceiras.\n\n"
     "O McCrea nasceu no Projeto de Modelagem de Sistemas (2026) com uma ideia simples: "
     "quem leva a embalagem até a máquina ganha pontos, e os pontos viram desconto nas lojas parceiras."),
    ("O Brasil gera muito e recicla pouco",
     "De cada 100 kg de resíduo urbano, menos de 9 kg seguem para a reciclagem de materiais.\n\n"
     "• 81,6 milhões de toneladas de resíduos urbanos foram gerados em 2024: 384 kg por habitante.\n"
     "• Só 8,7% vão para a reciclagem mecânica. Quase dois terços chegam pelas mãos de catadores informais.\n"
     "• Na cidade de São Paulo, só 2,85% do lixo recolhido vem da coleta seletiva. A meta era 10%.\n\n"
     "Fontes: Abrema, Panorama dos Resíduos Sólidos 2025 (ano-base 2024); "
     "Faculdade de Saúde Pública da USP (dados de 2024)."),
    ("A barreira é acesso e incentivo",
     "99% dos brasileiros reconhecem que reciclar é importante. A intenção existe: falta um ponto de entrega "
     "no caminho e um motivo imediato para usá-lo.\n\n"
     "Motivos de quem não recicla:\n"
     "• 42%: falta de acesso à coleta seletiva\n"
     "• 21%: preguiça\n"
     "• 18%: falta de informação sobre como reciclar\n\n"
     "Em outra pesquisa, 39% dos que não reciclam dizem não conhecer um ponto de coleta perto de casa.\n\n"
     "Fontes: pesquisa nacional com 2.010 entrevistas em 112 municípios, via Jovem Pan (dez. 2024); "
     "Samsung e MindMiners (2022)."),
    ("Onde há recompensa, a reciclagem acontece",
     "97,3% das latas de alumínio vendidas no Brasil em 2024 foram recicladas: 33,9 bilhões de unidades. "
     "A lata vale dinheiro na hora da entrega. O McCrea leva essa lógica às demais embalagens.\n\n"
     "• Latas de alumínio (Brasil): 97,3%\n"
     "• Embalagens com depósito (Alemanha): 96–99%\n"
     "• Resíduos urbanos (Brasil): 8,7%\n"
     "• Coleta seletiva (São Paulo): 2,85%\n\n"
     "Fontes: Recicla Latas (2025); Agência Federal de Meio Ambiente da Alemanha, via Euronews (2026); "
     "Abrema (2025); FSP-USP."),
    ("Como o McCrea funciona",
     "1. Deposita: a pessoa leva a embalagem à máquina mais próxima de casa.\n"
     "2. Pontua: infravermelho e visão computacional identificam o material e creditam os pontos.\n"
     "3. Avança: os pontos liberam fases no mapa de cupons, uma por marca parceira.\n"
     "4. Resgata: o cupom vira desconto na loja e leva um cliente novo à marca.\n\n"
     "Três peças trabalham juntas: a máquina (infravermelho e visão computacional), o aplicativo "
     "(mapa, pontos e fases de cupons) e o painel (depósitos e resgates por bairro)."),
    ("O protótipo já funciona",
     "• Mapa de máquinas: MapLibre e OpenFreeMap, sem chave de API nem cartão.\n"
     "• Mundo de cupons: seis fases; cada uma libera o cupom de uma marca.\n"
     "• Painel e planilha: depósitos por bairro e planilha gerada a partir do banco.\n\n"
     "Feito com Python (Flask), SQLite e HTML/JS puro. Nesta versão, a leitura da máquina é simulada."),
    ("A máquina mais próxima de cada casa",
     "A partir do endereço fixo do cadastro, o McCrea ordena as máquinas por proximidade usando a "
     "distância em linha reta: d = √(Δlat² + Δlng²), convertida para km (1° ≈ 111 km).\n\n"
     "• Simples: poucas operações aritméticas por máquina.\n"
     "• Barato: sem API paga e sem GPS em tempo real.\n"
     "• Privado: usa só o endereço fixo do cadastro.\n\n"
     "É uma linha reta, não uma rota: serve para ordenar as máquinas por proximidade."),
    ("O cupom já move o consumidor brasileiro",
     "• 70% economizam com cupons todos os meses.\n"
     "• 80% dizem que o cupom influencia onde vão comprar.\n"
     "• 53% poupam mais de R$ 50 por mês com cupons.\n\n"
     "No McCrea, a pessoa paga o cupom com embalagens, não com dinheiro.\n\n"
     "Fidelidade no 1º trimestre de 2026: 306 milhões de cadastros em programas de fidelidade, "
     "com R$ 6,3 bilhões de faturamento no trimestre.\n\n"
     "Fontes: Serasa e Opinion Box (maio de 2026, 1.051 entrevistas); ABEMF, indicadores do 1º trimestre de 2026."),
    ("A lei já exige coleta das marcas",
     "• 2010, Lei 12.305 (PNRS): fabricantes, comerciantes e consumidores compartilham a responsabilidade "
     "pelo ciclo de vida das embalagens.\n"
     "• 2023, Decreto 11.413: certificados de crédito de reciclagem passam a comprovar a logística reversa.\n"
     "• 2025, Decreto 12.688: plástico deve recuperar 32% das embalagens em 2026 e ter um ponto de entrega "
     "a cada 10 mil habitantes até 2029.\n\n"
     "Cada máquina é um ponto de entrega que registra item, material, data e local: dado rastreável para os "
     "programas de logística reversa das marcas.\n\n"
     "Fontes: Lei 12.305/2010; Decreto 11.413/2023; Decreto 12.688/2025 (texto oficial e análise de Felsberg Advogados)."),
    ("O que a marca parceira ganha",
     "O cupom leva quem recicla até a loja parceira do bairro.\n\n"
     "• Clientes novos: quem recicla recebe um motivo para experimentar a marca pela primeira vez. "
     "64% já compraram algo fora do planejado por causa de um cupom.\n"
     "• Custo por venda: o desconto só é concedido quando a venda acontece, e cada resgate fica registrado. "
     "73% já desistiram de uma compra por falta de cupom válido.\n"
     "• Imagem ambiental: cada resgate liga a marca a um gesto concreto de reciclagem, com dados por bairro. "
     "95% dizem priorizar empresas com práticas sustentáveis.\n\n"
     "Fontes: Serasa e Opinion Box (maio de 2026); pesquisa encomendada pela APAS, divulgada na APAS Show 2023."),
    ("O ecossistema e suas trocas",
     "• Morador: entrega embalagens na máquina e recebe pontos e cupons de desconto.\n"
     "• Marca parceira: entrega cupons e patrocínio de máquinas e recebe clientes novos e dados de reciclagem.\n"
     "• Cooperativas: fazem a coleta e a triagem e recebem material já separado, em volume previsível.\n"
     "• Cidade: oferece locais para as máquinas e ganha menos aterro e mais pontos de entrega.\n"
     "• McCrea: fornece máquinas, aplicativo e painel e recebe taxa por resgate, patrocínio e material.\n\n"
     "Papéis previstos no modelo de negócio; parcerias com marcas, cooperativas e prefeitura ainda a firmar."),
    ("Receita e riscos do modelo",
     "Receita prevista:\n"
     "• Taxa por cupom resgatado, paga pela marca parceira.\n"
     "• Patrocínio de máquina: mensalidade para a marca aparecer na máquina e no aplicativo.\n"
     "• Material e créditos de reciclagem vendidos à indústria recicladora.\n\n"
     "Riscos e respostas:\n"
     "• Custo das máquinas: piloto pequeno, em locais de alto fluxo, com máquinas patrocinadas.\n"
     "• Leitura ainda simulada: validar infravermelho e visão computacional em bancada antes do piloto.\n"
     "• Dados pessoais (LGPD): endereço fixo, sem localização em tempo real; dados anônimos para as marcas.\n\n"
     "Os valores ainda serão definidos com o levantamento de custos do projeto."),
    ("Reciclar vira desconto. O desconto vira cliente.",
     "Reciclar vira desconto. O desconto vira cliente. O cliente financia a próxima máquina.\n\n"
     "Próximo passo: um piloto com máquinas e marcas parceiras em São Paulo.\n\n"
     "Código do projeto: github.com/pbdo888/Projeto-Modelagem"),
]


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


def seed_anuncios(con):
    con.executemany("INSERT INTO anuncios (titulo, texto, imagem, ordem) VALUES (?,?,?,?)", [
        (titulo, texto, f"/static/cartazes/mccrea-{i:02d}.png", i)
        for i, (titulo, texto) in enumerate(ANUNCIOS_INICIAIS, start=1)])


def init_db():
    con = sqlite3.connect(DB_PATH)
    # Os cartazes iniciais entram só quando a tabela é criada; se o admin excluir todos, não voltam.
    sem_anuncios = not con.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'anuncios'").fetchone()
    con.executescript(SCHEMA)
    if con.execute("SELECT COUNT(*) FROM maquinas").fetchone()[0] == 0:
        seed(con)
    if sem_anuncios:
        seed_anuncios(con)
    migrar(con)
    con.commit()
    con.close()
