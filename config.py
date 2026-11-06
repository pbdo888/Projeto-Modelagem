"""
Configuração do McCrea: o que vem do ambiente (.env no computador, painel Environment na Render).

    SECRET_KEY   assina o cookie de login; sem ela, todos são deslogados a cada reinício do servidor
    ADMIN_TOKEN  token do painel de admin (header X-Admin-Token); vazio = admin desligado
    RENDER       a Render define sozinha; com ela, o cookie de sessão só trafega por HTTPS
"""
import os
import secrets

from dotenv import load_dotenv

from models.anuncio import MAX_IMAGEM_MB

load_dotenv()


class Config:
    """Valores lidos pelo Flask e pelos controllers (app.config)."""

    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = bool(os.getenv("RENDER"))  # na Render o site é servido só por HTTPS

    MAX_CONTENT_LENGTH = (MAX_IMAGEM_MB + 1) * 1024 * 1024  # imagem do cartaz + campos de texto
