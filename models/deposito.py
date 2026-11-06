"""Deposito: a leitura da máquina (material e quantidade) que vira pontos para o usuário."""
from models.banco import get_db
from models.erros import Conflito, DadosInvalidos, NaoEncontrado
from models.regras import PONTOS_MATERIAL


class Deposito:
    """Depósito de embalagens numa máquina (tabela depositos)."""

    @staticmethod
    def registrar(d):
        """Registra o depósito, ocupa a máquina e credita os pontos; devolve os pontos ganhos.

        Na versão atual a leitura é simulada pelo admin. Em produção, a máquina (sensor
        infravermelho + modelo de visão computacional) enviaria material e quantidade."""
        try:
            uid, mid, qtd, mat = int(d["usuario_id"]), int(d["maquina_id"]), int(d["quantidade"]), str(d["material"])
        except (KeyError, ValueError, TypeError):
            raise DadosInvalidos("dados inválidos")
        if mat not in PONTOS_MATERIAL or qtd < 1:
            raise DadosInvalidos("material ou quantidade inválidos")
        pts, con = qtd * PONTOS_MATERIAL[mat], get_db()
        if con.execute("UPDATE maquinas SET ocupacao = ocupacao + ? WHERE id = ? AND status = 'ativa' "
                       "AND ocupacao + ? <= capacidade", (qtd, mid, qtd)).rowcount == 0:
            raise Conflito("máquina indisponível ou cheia")
        if con.execute("UPDATE usuarios SET pontos = pontos + ? WHERE id = ?", (pts, uid)).rowcount == 0:
            con.rollback()  # desfaz a ocupação da máquina
            raise NaoEncontrado("usuário não encontrado")
        con.execute("INSERT INTO depositos (usuario_id, maquina_id, material, quantidade, pontos) VALUES (?,?,?,?,?)",
                    (uid, mid, mat, qtd, pts))
        con.commit()
        return pts
