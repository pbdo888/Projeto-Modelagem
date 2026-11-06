"""Máquinas McCrea: lista do mapa, máquinas mais próximas e cadastro pelo admin."""
from flask import jsonify, request

from controllers.autenticacao import requer_admin
from models.maquina import Maquina


def listar_maquinas():
    """GET /api/maquinas: máquinas ativas (para o mapa)."""
    return jsonify(Maquina.listar_ativas())


@requer_admin
def criar_maquina():
    """POST /api/maquinas (admin): cadastra uma máquina e devolve o id."""
    mid = Maquina.criar(request.get_json(silent=True) or {})
    return jsonify(id=mid), 201


def maquinas_proximas():
    """GET /api/maquinas/proximas?lat=&lng=: as 3 máquinas ativas mais próximas."""
    return jsonify(Maquina.proximas(request.args))
