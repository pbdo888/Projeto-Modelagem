"""Notícias: anúncios com cartaz no carrossel (lista pública) e gestão pelo admin."""
import os

from flask import jsonify, request, send_from_directory

from controllers.autenticacao import requer_admin
from models.anuncio import UPLOAD_ANUNCIOS, Anuncio


def cartaz(nome):
    """GET /uploads/anuncios/<nome>: um cartaz enviado pelo admin."""
    return send_from_directory(os.path.abspath(UPLOAD_ANUNCIOS), nome, max_age=86400)


def listar_anuncios():
    """GET /api/anuncios: anúncios publicados, na ordem do carrossel."""
    return jsonify(Anuncio.listar_publicados())


def ver_anuncio(aid):
    """GET /api/anuncios/<id>: um anúncio publicado completo ("Saiba mais")."""
    return jsonify(Anuncio.buscar_publicado(aid))


@requer_admin
def listar_anuncios_admin():
    """GET /api/admin/anuncios (admin): todos os anúncios, inclusive os ocultos."""
    return jsonify(Anuncio.listar_todos())


@requer_admin
def criar_anuncio():
    """POST /api/anuncios (admin, multipart): novo anúncio com cartaz."""
    return jsonify(Anuncio.criar(request.form, request.files.get("imagem"))), 201


@requer_admin
def editar_anuncio(aid):
    """PUT /api/anuncios/<id> (admin, multipart): edita o anúncio; o cartaz novo é opcional."""
    antigo = Anuncio.buscar(aid)  # 404 antes de ler o formulário enviado
    return jsonify(Anuncio.editar(antigo, request.form, request.files.get("imagem")))


@requer_admin
def excluir_anuncio(aid):
    """DELETE /api/anuncios/<id> (admin): exclui o anúncio e o cartaz enviado."""
    Anuncio.excluir(aid)
    return jsonify(ok=True)
