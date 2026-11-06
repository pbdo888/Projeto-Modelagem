"""Controle de acesso: rotas só de administrador (token) e rotas que exigem usuário logado (sessão)."""
import secrets
from functools import wraps

from flask import current_app, make_response, request, session

from controllers.respostas import erro, resposta_de_erro
from models.erros import ErroDeNegocio
from models.usuario import Usuario


def admin_ok():
    """True se a requisição trouxe o X-Admin-Token certo (comparação em tempo constante)."""
    token = request.headers.get("X-Admin-Token", "")
    admin_token = current_app.config["ADMIN_TOKEN"]
    return bool(admin_token) and secrets.compare_digest(token.encode(), admin_token.encode())


def requer_admin(f):
    """Bloqueia a rota (401) para quem não envia o X-Admin-Token correto.
    As respostas protegidas nunca ficam em cache no navegador (nem as de erro)."""
    @wraps(f)
    def protegida(*args, **kwargs):
        if not admin_ok():
            return erro("acesso restrito a administradores", 401)
        try:
            resposta = f(*args, **kwargs)
        except ErroDeNegocio as e:
            resposta = resposta_de_erro(e)
        resp = make_response(resposta)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    return protegida


def requer_login(f):
    """Exige um usuário logado (cookie de sessão) e o entrega à rota como `u`."""
    @wraps(f)
    def protegida(*args, **kwargs):
        u = Usuario.buscar(session.get("uid"))
        if not u:
            session.clear()
            return erro("faça login para continuar", 401)
        return f(u, *args, **kwargs)
    return protegida
