"""Área do administrador: painel (View), planilha de usuários e análise por localização."""
import os

from flask import jsonify, render_template, send_file

from controllers.autenticacao import requer_admin
from models.analise import Analise
from models.anuncio import MAX_IMAGEM_MB
from models.planilha import Planilha
from models.regras import PONTOS_MATERIAL


@requer_admin
def admin_painel():
    """GET /api/admin/painel: o HTML do painel (formulários + estatísticas) só sai do servidor com o token."""
    return render_template("admin_painel.html", materiais=PONTOS_MATERIAL, max_mb=MAX_IMAGEM_MB)


@requer_admin
def baixar_planilha():
    """GET /api/admin/planilha: regera e baixa a planilha de usuários (dados pessoais: LGPD)."""
    Planilha.atualizar()
    return send_file(os.path.abspath(Planilha.CAMINHO), as_attachment=True, download_name="usuarios_mccrea.xlsx")


@requer_admin
def analise():
    """GET /api/analise: depósitos, itens e usuários por bairro e por material."""
    return jsonify(Analise.por_localizacao())
