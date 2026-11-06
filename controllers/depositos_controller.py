"""Depósitos: a leitura da máquina vira pontos para o usuário."""
from flask import jsonify, request

from controllers.autenticacao import requer_admin
from models.deposito import Deposito


@requer_admin
def depositar():
    """POST /api/depositos (admin): simula a leitura da máquina. Em produção, a máquina
    (sensor infravermelho + modelo de visão computacional) chamaria esta rota com material e quantidade."""
    pontos = Deposito.registrar(request.get_json(silent=True) or {})
    return jsonify(pontos=pontos), 201
