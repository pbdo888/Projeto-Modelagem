"""Respostas de erro da API: sempre {"erro": "mensagem"} com o código HTTP certo."""
from flask import jsonify

from models.anuncio import MAX_IMAGEM_MB
from models.erros import Conflito, DadosInvalidos, NaoAutenticado, NaoEncontrado

# Cada tipo de erro de negócio (levantado pelo Model) vira um código HTTP
CODIGO_HTTP = {DadosInvalidos: 400, NaoAutenticado: 401, NaoEncontrado: 404, Conflito: 409}


def erro(msg, code=400):
    """Resposta de erro no formato que o front-end lê: {"erro": msg}."""
    return jsonify(erro=msg), code


def resposta_de_erro(e):
    """Traduz um ErroDeNegocio do Model para a resposta HTTP (mensagem + código)."""
    for tipo, codigo in CODIGO_HTTP.items():
        if isinstance(e, tipo):
            return erro(str(e), codigo)
    return erro(str(e))


def upload_grande(_):
    """413: a requisição passou do limite do servidor (MAX_CONTENT_LENGTH)."""
    return erro(f"imagem muito grande (máximo {MAX_IMAGEM_MB} MB)", 413)
