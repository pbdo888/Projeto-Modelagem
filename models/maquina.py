"""Maquina: as máquinas de reciclagem McCrea espalhadas pela cidade."""
from models.banco import get_db, rows
from models.erros import DadosInvalidos, NaoEncontrado
from models.planilha import Planilha
from models.regras import dist_km


class Maquina:
    """Máquina de reciclagem (tabela maquinas). Só as 'ativa' aparecem no mapa."""

    @staticmethod
    def listar_ativas():
        """Todas as máquinas ativas."""
        return rows("SELECT * FROM maquinas WHERE status = 'ativa'")

    @staticmethod
    def criar(d):
        """Cadastra uma máquina (nome, lat, lng; endereço e bairro opcionais) e devolve o id."""
        try:
            nome, lat, lng = d["nome"].strip(), float(d["lat"]), float(d["lng"])
        except (KeyError, ValueError, TypeError, AttributeError):
            raise DadosInvalidos("informe nome, lat e lng")
        if not nome or not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise DadosInvalidos("nome ou coordenadas inválidos")
        con = get_db()
        cur = con.execute(
            "INSERT INTO maquinas (nome, endereco, bairro, lat, lng) VALUES (?,?,?,?,?)",
            (nome, d.get("endereco", ""), d.get("bairro", ""), lat, lng))
        con.commit()
        Planilha.atualizar()  # a coluna "máquina mais próxima" pode mudar
        return cur.lastrowid

    @staticmethod
    def proximas(args):
        """As 3 máquinas ativas mais próximas de (lat, lng), com a distância em km; a primeira é a mais próxima."""
        try:
            lat, lng = float(args["lat"]), float(args["lng"])
        except (KeyError, ValueError):
            raise DadosInvalidos("informe lat e lng")
        ms = Maquina.listar_ativas()
        if not ms:
            raise NaoEncontrado("nenhuma máquina ativa")
        for m in ms:
            m["distancia_km"] = round(dist_km(lat, lng, m["lat"], m["lng"]), 2)
        return sorted(ms, key=lambda m: m["distancia_km"])[:3]
