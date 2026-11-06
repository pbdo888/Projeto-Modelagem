"""Cupom: descontos das marcas parceiras, pagos com pontos."""
import secrets

from models.banco import get_db, one, rows
from models.erros import Conflito, DadosInvalidos, NaoEncontrado


class Cupom:
    """Cupom de uma marca parceira (tabela cupons); cada resgate gera um código (tabela resgates)."""

    @staticmethod
    def listar_ativos():
        """Cupons ativos, do mais barato ao mais caro."""
        return rows("SELECT * FROM cupons WHERE ativo = 1 ORDER BY custo")

    @staticmethod
    def criar(d):
        """Cadastra um cupom (marca, descricao, custo em pontos) e devolve o id."""
        try:
            marca, desc, custo = d["marca"].strip(), d["descricao"].strip(), int(d["custo"])
        except (KeyError, ValueError, TypeError, AttributeError):
            raise DadosInvalidos("informe marca, descricao e custo")
        if not marca or not desc or custo < 1:
            raise DadosInvalidos("dados inválidos")
        con = get_db()
        cur = con.execute("INSERT INTO cupons (marca, descricao, custo) VALUES (?,?,?)", (marca, desc, custo))
        con.commit()
        return cur.lastrowid

    @staticmethod
    def resgatar(u, d):
        """Troca pontos do usuário `u` pelo cupom pedido e devolve o código do resgate."""
        try:
            cid = int(d["cupom_id"])
        except (KeyError, ValueError, TypeError):
            raise DadosInvalidos("dados inválidos")
        c = one("SELECT * FROM cupons WHERE id = ? AND ativo = 1", (cid,))
        if not c:
            raise NaoEncontrado("cupom não encontrado")
        con = get_db()
        # débito atômico: só desconta se o saldo for suficiente
        if con.execute("UPDATE usuarios SET pontos = pontos - ? WHERE id = ? AND pontos >= ?",
                       (c["custo"], u["id"], c["custo"])).rowcount == 0:
            raise Conflito("pontos insuficientes")
        codigo = secrets.token_hex(4).upper()
        con.execute("INSERT INTO resgates (usuario_id, cupom_id, codigo, pontos) VALUES (?,?,?,?)",
                    (u["id"], cid, codigo, c["custo"]))
        con.commit()
        return codigo
