"""ReciclaVerde: API Flask + front (index.html). Rode com: python app.py"""
import math
import os
import re
import secrets
import sqlite3
import uuid
from datetime import date
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, g, jsonify, make_response, render_template, request, send_file, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from db import DB_PATH, PONTOS_ITEM_MEDIO, PONTOS_MATERIAL, dist_km, init_db
from planilha import PLANILHA_PATH, gerar_planilha

load_dotenv()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

app = Flask(__name__, template_folder=".")  # index.html fica na mesma pasta
# Assina o cookie de sessão. Sem SECRET_KEY no .env, todos são deslogados a cada reinício.
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

# Cartazes enviados pelo admin (os iniciais ficam em static/cartazes, versionados)
UPLOAD_ANUNCIOS = os.path.join("uploads", "anuncios")
URL_ANUNCIOS = "/uploads/anuncios/"
MAX_IMAGEM_MB = 5
app.config["MAX_CONTENT_LENGTH"] = (MAX_IMAGEM_MB + 1) * 1024 * 1024  # imagem + campos de texto
os.makedirs(UPLOAD_ANUNCIOS, exist_ok=True)
init_db()
gerar_planilha()

# Opções do cadastro (o front monta os <select> a partir destas listas)
SEXOS = ["Feminino", "Masculino", "Outro", "Prefiro não informar"]
ESTADOS_CIVIS = ["Solteiro(a)", "Casado(a)", "União estável", "Divorciado(a)", "Viúvo(a)", "Prefiro não informar"]
COMO_CONHECEU = ["Redes sociais", "Indicação de amigo", "Vi uma máquina na rua", "Notícia ou imprensa", "Outro"]
UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
       "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
IDADE_MINIMA = 13


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


@app.errorhandler(413)
def upload_grande(_):
    return erro(f"imagem muito grande (máximo {MAX_IMAGEM_MB} MB)", 413)


def admin_ok():
    token = request.headers.get("X-Admin-Token", "")
    return bool(ADMIN_TOKEN) and secrets.compare_digest(token.encode(), ADMIN_TOKEN.encode())


def requer_admin(f):
    """Bloqueia a rota (401) para quem não envia o X-Admin-Token correto.
    As respostas protegidas nunca ficam em cache no navegador."""
    @wraps(f)
    def protegida(*args, **kwargs):
        if not admin_ok():
            return erro("acesso restrito a administradores", 401)
        resp = make_response(f(*args, **kwargs))
        resp.headers["Cache-Control"] = "no-store"
        return resp
    return protegida


def requer_login(f):
    """Exige um usuário logado (cookie de sessão) e o entrega à rota como `u`."""
    @wraps(f)
    def protegida(*args, **kwargs):
        u = one("SELECT * FROM usuarios WHERE id = ?", (session.get("uid"),))
        if not u:
            session.clear()
            return erro("faça login para continuar", 401)
        return f(u, *args, **kwargs)
    return protegida


def publico(u):
    """Dados do usuário que podem ir para o navegador (nunca o hash da senha)."""
    return {k: v for k, v in u.items() if k != "senha_hash"}


def atualizar_planilha():
    if not gerar_planilha():
        app.logger.warning("Não deu para atualizar %s: feche o arquivo no Excel.", PLANILHA_PATH)


# ---------- validação do cadastro ----------
def texto(d, campo, nome, obrigatorio=True, maximo=120):
    v = str(d.get(campo) or "").strip()
    if obrigatorio and not v:
        raise ValueError(f"informe {nome}")
    if len(v) > maximo:
        raise ValueError(f"{nome} muito longo")
    return v


def opcao(d, campo, nome, opcoes):
    v = str(d.get(campo) or "").strip()
    if v not in opcoes:
        raise ValueError(f"escolha {nome}")
    return v


def validar_endereco(d):
    cep = re.sub(r"\D", "", str(d.get("cep") or ""))
    if len(cep) != 8:
        raise ValueError("CEP inválido (8 dígitos)")
    try:
        lat, lng = float(d["lat"]), float(d["lng"])
    except (KeyError, ValueError, TypeError):
        raise ValueError("localize o endereço no mapa antes de continuar")
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        raise ValueError("coordenadas inválidas")
    return {
        "cep": f"{cep[:5]}-{cep[5:]}",
        "logradouro": texto(d, "logradouro", "a rua"),
        "numero": texto(d, "numero", "o número", maximo=10),
        "complemento": texto(d, "complemento", "o complemento", obrigatorio=False, maximo=60),
        "bairro": texto(d, "bairro", "o bairro", maximo=60),
        "cidade": texto(d, "cidade", "a cidade", maximo=60),
        "uf": opcao(d, "uf", "o estado (UF)", UFS),
        "lat": lat, "lng": lng,
    }


def validar_cadastro(d):
    email = str(d.get("email") or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise ValueError("e-mail inválido")
    senha = str(d.get("senha") or "")
    if len(senha) < 6:
        raise ValueError("a senha precisa ter pelo menos 6 caracteres")
    try:
        nasc = date.fromisoformat(str(d.get("nascimento")))
    except ValueError:
        raise ValueError("data de nascimento inválida")
    hoje = date.today()
    anos = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
    if anos < IDADE_MINIMA or anos > 120:
        raise ValueError(f"é preciso ter pelo menos {IDADE_MINIMA} anos para se cadastrar")
    tel = re.sub(r"\D", "", str(d.get("telefone") or ""))
    if len(tel) not in (10, 11):
        raise ValueError("telefone inválido (DDD + número)")
    try:
        moradores = int(d.get("moradores"))
    except (TypeError, ValueError):
        raise ValueError("informe quantas pessoas moram na sua casa")
    if not 1 <= moradores <= 30:
        raise ValueError("número de moradores inválido")
    como = str(d.get("como_conheceu") or "").strip()
    if como and como not in COMO_CONHECEU:
        raise ValueError("opção inválida em 'como conheceu'")
    if d.get("aceite_termos") is not True:
        raise ValueError("é preciso aceitar os termos de uso e a política de privacidade")
    return {
        "nome": texto(d, "nome", "o nome completo"),
        "email": email,
        "senha_hash": generate_password_hash(senha),
        "nascimento": nasc.isoformat(),
        "sexo": opcao(d, "sexo", "o sexo", SEXOS),
        "estado_civil": opcao(d, "estado_civil", "o estado civil", ESTADOS_CIVIS),
        "telefone": f"({tel[:2]}) {tel[2:-4]}-{tel[-4:]}",
        "moradores": moradores,
        "como_conheceu": como or None,
        "aceita_ofertas": 1 if d.get("aceita_ofertas") else 0,
        **validar_endereco(d),
    }


@app.get("/")
def index():
    # template_folder="." faz o caminho do template partir da raiz do projeto
    return render_template("templates/casa.html")


@app.get("/app")
def app_principal():
    """O app completo (mapa, login, cadastro, notícias, admin), que antes ficava em '/'."""
    return render_template("index.html", sexos=SEXOS, estados_civis=ESTADOS_CIVIS,
                           como_conheceu=COMO_CONHECEU, ufs=UFS)


@app.get("/api/admin/painel")
@requer_admin
def admin_painel():
    """O HTML do painel (formulários + estatísticas) só sai do servidor com o token válido."""
    return render_template("admin_painel.html", materiais=PONTOS_MATERIAL, max_mb=MAX_IMAGEM_MB)


@app.get("/api/admin/planilha")
@requer_admin
def baixar_planilha():
    atualizar_planilha()
    return send_file(os.path.abspath(PLANILHA_PATH), as_attachment=True, download_name="usuarios_reciclaverde.xlsx")


# ---------- máquinas ----------
@app.get("/api/maquinas")
def listar_maquinas():
    return jsonify(rows("SELECT * FROM maquinas WHERE status = 'ativa'"))


@app.post("/api/maquinas")
@requer_admin
def criar_maquina():
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
    atualizar_planilha()  # a coluna "máquina mais próxima" pode mudar
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


# ---------- conta: cadastro, login e endereço ----------
@app.post("/api/cadastro")
def cadastro():
    d = request.get_json(silent=True) or {}
    try:
        dados = validar_cadastro(d)
    except ValueError as e:
        return erro(str(e))
    con = get_db()
    existente = one("SELECT id, senha_hash FROM usuarios WHERE email = ?", (dados["email"],))
    if existente and existente["senha_hash"]:
        return erro("este e-mail já tem cadastro; use Entrar", 409)
    cols = list(dados)
    if existente:  # conta antiga (só e-mail, sem senha): completa o cadastro e mantém os pontos
        con.execute(f"UPDATE usuarios SET {', '.join(c + ' = ?' for c in cols)}, aceite_termos_em = CURRENT_TIMESTAMP "
                    "WHERE id = ?", [*dados.values(), existente["id"]])
        uid = existente["id"]
    else:
        uid = con.execute(f"INSERT INTO usuarios ({', '.join(cols)}, aceite_termos_em) "
                          f"VALUES ({', '.join('?' * len(cols))}, CURRENT_TIMESTAMP)", list(dados.values())).lastrowid
    con.commit()
    session.clear()
    session["uid"] = uid
    atualizar_planilha()
    return jsonify(publico(one("SELECT * FROM usuarios WHERE id = ?", (uid,)))), 201


@app.post("/api/login")
def login():
    d = request.get_json(silent=True) or {}
    email, senha = str(d.get("email", "")).strip().lower(), str(d.get("senha", ""))
    u = one("SELECT * FROM usuarios WHERE email = ?", (email,))
    if u and not u["senha_hash"]:
        return erro("conta antiga: finalize seu cadastro para criar uma senha", 409)
    if not u or not check_password_hash(u["senha_hash"], senha):
        return erro("e-mail ou senha incorretos", 401)
    session.clear()
    session["uid"] = u["id"]
    return jsonify(publico(u))


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify(ok=True)


@app.post("/api/eu/endereco")
@requer_login
def mudar_endereco(u):
    try:
        end = validar_endereco(request.get_json(silent=True) or {})
    except ValueError as e:
        return erro(str(e))
    con = get_db()
    con.execute(f"UPDATE usuarios SET {', '.join(c + ' = ?' for c in end)} WHERE id = ?", [*end.values(), u["id"]])
    con.commit()
    atualizar_planilha()
    return jsonify(ok=True)


@app.get("/api/eu")
@requer_login
def progresso(u):
    # Mapa de fases: cada cupom ativo é uma fase, em ordem de custo. A fase é liberada pelos
    # pontos acumulados (soma dos depósitos), que nunca diminuem; assim o avatar não volta
    # no mapa quando o usuário resgata um cupom. O resgate continua gastando o saldo (pontos).
    uid = u["id"]
    total = one("SELECT COALESCE(SUM(pontos), 0) AS t FROM depositos WHERE usuario_id = ?", (uid,))["t"]
    resgates = {r["cupom_id"]: r["n"] for r in rows(
        "SELECT cupom_id, COUNT(*) AS n FROM resgates WHERE usuario_id = ? GROUP BY cupom_id", (uid,))}
    fases = [dict(c, fase=i + 1, liberada=total >= c["custo"], resgatavel=u["pontos"] >= c["custo"],
                  resgates=resgates.get(c["id"], 0))
             for i, c in enumerate(rows("SELECT * FROM cupons WHERE ativo = 1 ORDER BY custo, id"))]
    prox = next((f for f in fases if not f["liberada"]), None)
    faltam = prox["custo"] - total if prox else 0
    return jsonify(usuario=publico(u), pontos_totais=total, fases=fases,
                   fase_atual=sum(f["liberada"] for f in fases),  # 0 = ainda no início do mapa
                   proximo_cupom=prox, faltam_pontos=faltam,
                   faltam_itens=math.ceil(faltam / PONTOS_ITEM_MEDIO))


@app.post("/api/depositos")
@requer_admin
def depositar():
    """Simula a leitura da máquina. Em produção, a máquina (sensor infravermelho +
    modelo de visão computacional) chamaria este endpoint com material e quantidade."""
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
@requer_admin
def criar_cupom():
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
@requer_login
def resgatar(u):
    d = request.get_json(silent=True) or {}
    try:
        cid = int(d["cupom_id"])
    except (KeyError, ValueError, TypeError):
        return erro("dados inválidos")
    c = one("SELECT * FROM cupons WHERE id = ? AND ativo = 1", (cid,))
    if not c:
        return erro("cupom não encontrado", 404)
    con = get_db()
    # débito atômico: só desconta se o saldo for suficiente
    if con.execute("UPDATE usuarios SET pontos = pontos - ? WHERE id = ? AND pontos >= ?",
                   (c["custo"], u["id"], c["custo"])).rowcount == 0:
        return erro("pontos insuficientes", 409)
    codigo = secrets.token_hex(4).upper()
    con.execute("INSERT INTO resgates (usuario_id, cupom_id, codigo, pontos) VALUES (?,?,?,?)",
                (u["id"], cid, codigo, c["custo"]))
    con.commit()
    return jsonify(codigo=codigo)


# ---------- notícias: anúncios com cartaz (carrossel) ----------
def tipo_imagem(dados):
    """Extensão pelo conteúdo do arquivo (não confia no nome nem no Content-Type). SVG fica de fora (pode ter script)."""
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if dados.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if dados[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "webp"
    return None


def validar_anuncio(d):
    titulo = texto(d, "titulo", "o título", maximo=120)
    if len(titulo) < 3:
        raise ValueError("o título precisa ter pelo menos 3 caracteres")
    try:
        ordem = int(d.get("ordem") or 0)
    except (TypeError, ValueError):
        raise ValueError("ordem inválida")
    if not 0 <= ordem <= 9999:
        raise ValueError("a ordem deve ficar entre 0 e 9999")
    return {
        "titulo": titulo,
        "texto": texto(d, "texto", "o texto do anúncio", maximo=5000),
        "ordem": ordem,
        "ativo": 1 if str(d.get("ativo", "1")).lower() in ("1", "true", "on", "sim") else 0,
    }


def salvar_cartaz(obrigatorio):
    """Grava o cartaz enviado em uploads/anuncios com nome aleatório e devolve o caminho público."""
    arq = request.files.get("imagem")
    if not arq or not arq.filename:
        if obrigatorio:
            raise ValueError("envie a imagem do cartaz")
        return None
    dados = arq.read()
    if len(dados) > MAX_IMAGEM_MB * 1024 * 1024:
        raise ValueError(f"imagem muito grande (máximo {MAX_IMAGEM_MB} MB)")
    ext = tipo_imagem(dados)
    if not ext:
        raise ValueError("formato de imagem inválido (use PNG, JPG, WebP ou GIF)")
    nome = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(UPLOAD_ANUNCIOS, nome), "wb") as f:
        f.write(dados)
    return URL_ANUNCIOS + nome


def apagar_cartaz(url):
    """Só apaga arquivos enviados pelo admin; os cartazes iniciais (static/) ficam."""
    if url and url.startswith(URL_ANUNCIOS):
        try:
            os.remove(os.path.join(UPLOAD_ANUNCIOS, os.path.basename(url)))
        except OSError:
            pass


@app.get(URL_ANUNCIOS + "<path:nome>")
def cartaz(nome):
    return send_from_directory(os.path.abspath(UPLOAD_ANUNCIOS), nome, max_age=86400)


@app.get("/api/anuncios")
def listar_anuncios():
    return jsonify(rows("SELECT id, titulo, texto, imagem, criado_em FROM anuncios WHERE ativo = 1 "
                        "ORDER BY ordem, id DESC"))


@app.get("/api/anuncios/<int:aid>")
def ver_anuncio(aid):
    a = one("SELECT id, titulo, texto, imagem, criado_em FROM anuncios WHERE id = ? AND ativo = 1", (aid,))
    return jsonify(a) if a else erro("anúncio não encontrado", 404)


@app.get("/api/admin/anuncios")
@requer_admin
def listar_anuncios_admin():
    return jsonify(rows("SELECT * FROM anuncios ORDER BY ordem, id DESC"))


@app.post("/api/anuncios")
@requer_admin
def criar_anuncio():
    try:
        dados = validar_anuncio(request.form)
        dados["imagem"] = salvar_cartaz(obrigatorio=True)
    except ValueError as e:
        return erro(str(e))
    con = get_db()
    cur = con.execute(f"INSERT INTO anuncios ({', '.join(dados)}) VALUES ({', '.join('?' * len(dados))})",
                      list(dados.values()))
    con.commit()
    return jsonify(one("SELECT * FROM anuncios WHERE id = ?", (cur.lastrowid,))), 201


@app.put("/api/anuncios/<int:aid>")
@requer_admin
def editar_anuncio(aid):
    antigo = one("SELECT * FROM anuncios WHERE id = ?", (aid,))
    if not antigo:
        return erro("anúncio não encontrado", 404)
    try:
        dados = validar_anuncio(request.form)
        nova = salvar_cartaz(obrigatorio=False)  # sem imagem nova, mantém o cartaz atual
    except ValueError as e:
        return erro(str(e))
    if nova:
        dados["imagem"] = nova
    con = get_db()
    con.execute(f"UPDATE anuncios SET {', '.join(c + ' = ?' for c in dados)}, atualizado_em = CURRENT_TIMESTAMP "
                "WHERE id = ?", [*dados.values(), aid])
    con.commit()
    if nova:
        apagar_cartaz(antigo["imagem"])
    return jsonify(one("SELECT * FROM anuncios WHERE id = ?", (aid,)))


@app.delete("/api/anuncios/<int:aid>")
@requer_admin
def excluir_anuncio(aid):
    a = one("SELECT imagem FROM anuncios WHERE id = ?", (aid,))
    if not a:
        return erro("anúncio não encontrado", 404)
    con = get_db()
    con.execute("DELETE FROM anuncios WHERE id = ?", (aid,))
    con.commit()
    apagar_cartaz(a["imagem"])
    return jsonify(ok=True)


# ---------- análise por localização ----------
@app.get("/api/analise")
@requer_admin
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
