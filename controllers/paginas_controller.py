"""Páginas do site: entregam as Views (templates em views/)."""
from flask import render_template

from models.usuario import Usuario


def index():
    """GET /: a Home (praça com as máquinas McCrea, carrossel de anúncios e Banco de Cupons)."""
    return render_template("casa.html")


def app_principal():
    """GET /app: o app completo (mapa, login, cadastro, notícias, admin), que antes ficava em '/'.
    As opções dos <select> do cadastro vêm do Model Usuario."""
    return render_template("index.html", sexos=Usuario.SEXOS, estados_civis=Usuario.ESTADOS_CIVIS,
                           como_conheceu=Usuario.COMO_CONHECEU, ufs=Usuario.UFS)
