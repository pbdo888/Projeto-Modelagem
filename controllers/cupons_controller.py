"""Cupons: lista pública, criação pelo admin e resgate com pontos."""
from flask import jsonify, request

from controllers.autenticacao import requer_admin, requer_login
from models.cupom import Cupom


def listar_cupons():
    """GET /api/cupons: cupons ativos, do mais barato ao mais caro."""
    return jsonify(Cupom.listar_ativos())


@requer_admin
def criar_cupom():
    """POST /api/cupons (admin): cadastra o cupom de uma marca parceira e devolve o id."""
    cid = Cupom.criar(request.get_json(silent=True) or {})
    return jsonify(id=cid), 201


@requer_login
def resgatar(u):
    """POST /api/resgatar: troca pontos do usuário logado por um cupom e devolve o código."""
    codigo = Cupom.resgatar(u, request.get_json(silent=True) or {})
    return jsonify(codigo=codigo)
