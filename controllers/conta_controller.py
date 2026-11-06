"""Conta do usuário: cadastro, login, logout, endereço fixo e progresso no mapa de cupons."""
from flask import jsonify, request, session

from controllers.autenticacao import requer_login
from models.usuario import Usuario


def _abrir_sessao(uid):
    """Guarda o usuário no cookie de sessão (assinado com a SECRET_KEY)."""
    session.clear()
    session["uid"] = uid


def cadastro():
    """POST /api/cadastro: cria a conta (ou completa uma conta antiga) e já entra nela."""
    uid = Usuario.cadastrar(request.get_json(silent=True) or {})
    _abrir_sessao(uid)
    return jsonify(Usuario.publico(Usuario.buscar(uid))), 201


def login():
    """POST /api/login: confere e-mail e senha e abre a sessão."""
    u = Usuario.autenticar(request.get_json(silent=True) or {})
    _abrir_sessao(u["id"])
    return jsonify(Usuario.publico(u))


def logout():
    """POST /api/logout: encerra a sessão."""
    session.clear()
    return jsonify(ok=True)


@requer_login
def mudar_endereco(u):
    """POST /api/eu/endereco: troca o endereço fixo do usuário logado."""
    Usuario.mudar_endereco(u["id"], request.get_json(silent=True) or {})
    return jsonify(ok=True)


@requer_login
def progresso(u):
    """GET /api/eu: dados do usuário logado, pontos e fases do mapa de cupons."""
    return jsonify(Usuario.progresso(u))
