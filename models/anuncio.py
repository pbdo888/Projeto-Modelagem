"""Anuncio: as notícias do carrossel, cada uma com um cartaz (imagem)."""
import os
import uuid

from models.banco import get_db, one, rows
from models.erros import DadosInvalidos, NaoEncontrado
from models.validacao import texto

# Cartazes enviados pelo admin (os iniciais ficam em static/cartazes, versionados)
UPLOAD_ANUNCIOS = os.path.join("uploads", "anuncios")
URL_ANUNCIOS = "/uploads/anuncios/"
MAX_IMAGEM_MB = 5


def tipo_imagem(dados):
    """Extensão pelo conteúdo do arquivo (não confia no nome nem no Content-Type). SVG fica de fora (pode ter script)."""
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if dados.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if dados[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "webp"
    return None


class Anuncio:
    """Anúncio do carrossel de Notícias (tabela anuncios). Ocultos (ativo=0) só o admin vê."""

    @staticmethod
    def preparar_pasta():
        """Cria uploads/anuncios, onde ficam os cartazes enviados pelo admin."""
        os.makedirs(UPLOAD_ANUNCIOS, exist_ok=True)

    @staticmethod
    def validar(d):
        """Campos do formulário do admin: título, texto, ordem no carrossel e se está publicado."""
        titulo = texto(d, "titulo", "o título", maximo=120)
        if len(titulo) < 3:
            raise DadosInvalidos("o título precisa ter pelo menos 3 caracteres")
        try:
            ordem = int(d.get("ordem") or 0)
        except (TypeError, ValueError):
            raise DadosInvalidos("ordem inválida")
        if not 0 <= ordem <= 9999:
            raise DadosInvalidos("a ordem deve ficar entre 0 e 9999")
        return {
            "titulo": titulo,
            "texto": texto(d, "texto", "o texto do anúncio", maximo=5000),
            "ordem": ordem,
            "ativo": 1 if str(d.get("ativo", "1")).lower() in ("1", "true", "on", "sim") else 0,
        }

    @staticmethod
    def salvar_cartaz(arquivo, obrigatorio):
        """Grava o cartaz enviado em uploads/anuncios com nome aleatório e devolve o caminho público."""
        if not arquivo or not arquivo.filename:
            if obrigatorio:
                raise DadosInvalidos("envie a imagem do cartaz")
            return None
        dados = arquivo.read()
        if len(dados) > MAX_IMAGEM_MB * 1024 * 1024:
            raise DadosInvalidos(f"imagem muito grande (máximo {MAX_IMAGEM_MB} MB)")
        ext = tipo_imagem(dados)
        if not ext:
            raise DadosInvalidos("formato de imagem inválido (use PNG, JPG, WebP ou GIF)")
        nome = f"{uuid.uuid4().hex}.{ext}"
        with open(os.path.join(UPLOAD_ANUNCIOS, nome), "wb") as f:
            f.write(dados)
        return URL_ANUNCIOS + nome

    @staticmethod
    def apagar_cartaz(url):
        """Só apaga arquivos enviados pelo admin; os cartazes iniciais (static/) ficam."""
        if url and url.startswith(URL_ANUNCIOS):
            try:
                os.remove(os.path.join(UPLOAD_ANUNCIOS, os.path.basename(url)))
            except OSError:
                pass

    @staticmethod
    def listar_publicados():
        """Anúncios publicados, na ordem do carrossel."""
        return rows("SELECT id, titulo, texto, imagem, criado_em FROM anuncios WHERE ativo = 1 "
                    "ORDER BY ordem, id DESC")

    @staticmethod
    def buscar_publicado(aid):
        """Um anúncio publicado ("Saiba mais")."""
        a = one("SELECT id, titulo, texto, imagem, criado_em FROM anuncios WHERE id = ? AND ativo = 1", (aid,))
        if not a:
            raise NaoEncontrado("anúncio não encontrado")
        return a

    @staticmethod
    def listar_todos():
        """Todos os anúncios, inclusive os ocultos (painel do admin)."""
        return rows("SELECT * FROM anuncios ORDER BY ordem, id DESC")

    @staticmethod
    def buscar(aid):
        """Qualquer anúncio (publicado ou não), com todas as colunas."""
        a = one("SELECT * FROM anuncios WHERE id = ?", (aid,))
        if not a:
            raise NaoEncontrado("anúncio não encontrado")
        return a

    @classmethod
    def criar(cls, form, arquivo):
        """Cria o anúncio com o cartaz enviado (obrigatório) e devolve o registro completo."""
        dados = cls.validar(form)
        dados["imagem"] = cls.salvar_cartaz(arquivo, obrigatorio=True)
        con = get_db()
        cur = con.execute(f"INSERT INTO anuncios ({', '.join(dados)}) VALUES ({', '.join('?' * len(dados))})",
                          list(dados.values()))
        con.commit()
        return one("SELECT * FROM anuncios WHERE id = ?", (cur.lastrowid,))

    @classmethod
    def editar(cls, antigo, form, arquivo):
        """Atualiza o anúncio `antigo`; com cartaz novo, apaga o enviado antes. Devolve o registro atualizado."""
        aid = antigo["id"]
        dados = cls.validar(form)
        nova = cls.salvar_cartaz(arquivo, obrigatorio=False)  # sem imagem nova, mantém o cartaz atual
        if nova:
            dados["imagem"] = nova
        con = get_db()
        con.execute(f"UPDATE anuncios SET {', '.join(c + ' = ?' for c in dados)}, atualizado_em = CURRENT_TIMESTAMP "
                    "WHERE id = ?", [*dados.values(), aid])
        con.commit()
        if nova:
            cls.apagar_cartaz(antigo["imagem"])
        return one("SELECT * FROM anuncios WHERE id = ?", (aid,))

    @classmethod
    def excluir(cls, aid):
        """Exclui o anúncio e o cartaz enviado por upload (se houver)."""
        a = one("SELECT imagem FROM anuncios WHERE id = ?", (aid,))
        if not a:
            raise NaoEncontrado("anúncio não encontrado")
        con = get_db()
        con.execute("DELETE FROM anuncios WHERE id = ?", (aid,))
        con.commit()
        cls.apagar_cartaz(a["imagem"])
