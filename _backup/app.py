"""ReciclaVerde: API Flask + front (index.html). Rode com: python app.py"""
import math
import os
import secrets
import sqlite3

from dotenv import load_dotenv
from flask import Flask, g, jsonify, render_template, request

from db import DB_PATH, PONTOS_ITEM_MEDIO, PONTOS_MATERIAL, init_db

load_dotenv()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")
MAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

app = Flask(__name__, template_folder=".")  # index.html fica na mesma pasta
init_db()


# ---------- utilidades ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def fechar_db(_):
    con = g.pop("db", None)
    if con is not None:
        con.close()


def rows(sql, args=()):
    return [dict(r) for r in get_db().execute(sql, args)]


def one(sql, args=()):
    r = get_db().execute(sql, args).fetchone()
    return dict(r) if r else None


def erro(msg, code=400):
    return jsonify(erro=msg), code


def admin_ok():
    token = request.headers.get("X-Admin-Token", "")
    return bool(ADMIN_TOKEN) and secrets.compare_digest(token.encode(), ADMIN_TOKEN.encode())


def dist_km(lat1, lng1, lat2, lng2):
    """Distância euclidiana no plano (lat, lng). Graus viram km: 1° ≈ 111,32 km,
    e a longitude é encolhida por cos(latitude) para não distorcer o resultado."""
    x = (lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = lat2 - lat1
    return 111.32 * math.hypot(x, y)


@app.get("/")
def index():
    return render_template("index.html", maps_key=MAPS_KEY, materiais=PONTOS_MATERIAL)


# ---------- máquinas ----------
@app.get("/api/maquinas")
def listar_maquinas():
    return jsonify(rows("SELECT * FROM maquinas WHERE status = 'ativa'"))


@app.post("/api/maquinas")
def criar_maquina():
    if not admin_ok():
        return erro("token de admin inválido (defina ADMIN_TOKEN no .env)", 401)
    d = request.get_json(silent=True) or {}
    try:
        nome, lat, lng = d["nome"].strip(), float(d["lat"]), float(d["lng"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return erro("informe nome, lat e lng")
    if not nome or not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return erro("nome ou coordenadas inválidos")
    con = get_db()
    cur = con.execute(
        "INSERT INTO maquinas (nome, endereco, bairro, lat, lng) VALUES (?,?,?,?,?)",
        (nome, d.get("endereco", ""), d.get("bairro", ""), lat, lng))
    con.commit()
    return jsonify(id=cur.lastrowid), 201


@app.get("/api/maquinas/proximas")
def maquinas_proximas():
    try:
        lat, lng = float(request.args["lat"]), float(request.args["lng"])
    except (KeyError, ValueError):
        return erro("informe lat e lng")
    ms = rows("SELECT * FROM maquinas WHERE status = 'ativa'")
    if not ms:
        return erro("nenhuma máquina ativa", 404)
    for m in ms:
        m["distancia_km"] = round(dist_km(lat, lng, m["lat"], m["lng"]), 2)
    return jsonify(sorted(ms, key=lambda m: m["distancia_km"])[:3])  # a primeira é a mais próxima


# ---------- usuários e pontos ----------
@app.post("/api/login")
def login():
    """Login simplificado por e-mail; no primeiro acesso cria a conta (precisa do nome)."""
    d = request.get_json(silent=True) or {}
    email, nome = str(d.get("email", "")).strip().lower(), str(d.get("nome", "")).strip()
    if "@" not in email:
        return erro("e-mail inválido")
    u = one("SELECT * FROM usuarios WHERE email = ?", (email,))
    if not u:
        if not nome:
            return erro("primeiro acesso: informe também o seu nome", 404)
        con = get_db()
        cur = con.execute("INSERT INTO usuarios (nome, email) VALUES (?,?)", (nome, email))
        con.commit()
        u = one("SELECT * FROM usuarios WHERE id = ?", (cur.lastrowid,))
    return jsonify(u)


@app.get("/api/usuarios/<int:uid>/progresso")
def progresso(uid):
    u = one("SELECT * FROM usuarios WHERE id = ?", (uid,))
    if not u:
        return erro("usuário não encontrado", 404)
    prox = one("SELECT * FROM cupons WHERE ativo = 1 AND custo > ? ORDER BY custo LIMIT 1", (u["pontos"],))
    faltam = prox["custo"] - u["pontos"] if prox else 0
    return jsonify(usuario=u, proximo_cupom=prox, faltam_pontos=faltam,
                   faltam_itens=math.ceil(faltam / PONTOS_ITEM_MEDIO))


@app.post("/api/depositos")
def depositar():
    """Simula a leitura da máquina. Em produção, a máquina (sensor infravermelho +
    modelo de visão computacional) chamaria este endpoint com material e quantidade."""
    if not admin_ok():
        return erro("token de admin inválido (defina ADMIN_TOKEN no .env)", 401)
    d = request.get_json(silent=True) or {}
    try:
        uid, mid, qtd, mat = int(d["usuario_id"]), int(d["maquina_id"]), int(d["quantidade"]), str(d["material"])
    except (KeyError, ValueError, TypeError):
        return erro("dados inválidos")
    if mat not in PONTOS_MATERIAL or qtd < 1:
        return erro("material ou quantidade inválidos")
    pts, con = qtd * PONTOS_MATERIAL[mat], get_db()
    if con.execute("UPDATE maquinas SET ocupacao = ocupacao + ? WHERE id = ? AND status = 'ativa' "
                   "AND ocupacao + ? <= capacidade", (qtd, mid, qtd)).rowcount == 0:
        return erro("máquina indisponível ou cheia", 409)
    if con.execute("UPDATE usuarios SET pontos = pontos + ? WHERE id = ?", (pts, uid)).rowcount == 0:
        con.rollback()
        return erro("usuário não encontrado", 404)
    con.execute("INSERT INTO depositos (usuario_id, maquina_id, material, quantidade, pontos) VALUES (?,?,?,?,?)",
                (uid, mid, mat, qtd, pts))
    con.commit()
    return jsonify(pontos=pts), 201


# ---------- cupons ----------
@app.get("/api/cupons")
def listar_cupons():
    return jsonify(rows("SELECT * FROM cupons WHERE ativo = 1 ORDER BY custo"))


@app.post("/api/cupons")
def criar_cupom():
    if not admin_ok():
        return erro("token de admin inválido (defina ADMIN_TOKEN no .env)", 401)
    d = request.get_json(silent=True) or {}
    try:
        marca, desc, custo = d["marca"].strip(), d["descricao"].strip(), int(d["custo"])
    except (KeyError, ValueError, TypeError, AttributeError):
        return erro("informe marca, descricao e custo")
    if not marca or not desc or custo < 1:
        return erro("dados inválidos")
    con = get_db()
    cur = con.execute("INSERT INTO cupons (marca, descricao, custo) VALUES (?,?,?)", (marca, desc, custo))
    con.commit()
    return jsonify(id=cur.lastrowid), 201


@app.post("/api/resgatar")
def resgatar():
    d = request.get_json(silent=True) or {}
    try:
        uid, cid = int(d["usuario_id"]), int(d["cupom_id"])
    except (KeyError, ValueError, TypeError):
        return erro("dados inválidos")
    c = one("SELECT * FROM cupons WHERE id = ? AND ativo = 1", (cid,))
    if not c:
        return erro("cupom não encontrado", 404)
    con = get_db()
    # débito atômico: só desconta se o saldo for suficiente
    if con.execute("UPDATE usuarios SET pontos = pontos - ? WHERE id = ? AND pontos >= ?",
                   (c["custo"], uid, c["custo"])).rowcount == 0:
        return erro("pontos insuficientes ou usuário inexistente", 409)
    codigo = secrets.token_hex(4).upper()
    con.execute("INSERT INTO resgates (usuario_id, cupom_id, codigo, pontos) VALUES (?,?,?,?)",
                (uid, cid, codigo, c["custo"]))
    con.commit()
    return jsonify(codigo=codigo)


# ---------- análise por localização ----------
@app.get("/api/analise")
def analise():
    por_bairro = rows("""
        SELECT m.bairro, COUNT(DISTINCT m.id) AS maquinas, COUNT(d.id) AS depositos,
               COALESCE(SUM(d.quantidade), 0) AS itens, COALESCE(SUM(d.pontos), 0) AS pontos,
               COUNT(DISTINCT d.usuario_id) AS usuarios
        FROM maquinas m LEFT JOIN depositos d ON d.maquina_id = m.id
        GROUP BY m.bairro ORDER BY itens DESC""")
    por_material = rows(
        "SELECT material, SUM(quantidade) AS itens FROM depositos GROUP BY material ORDER BY itens DESC")
    return jsonify(por_bairro=por_bairro, por_material=por_material)


if __name__ == "__main__":
    app.run(debug=True)
