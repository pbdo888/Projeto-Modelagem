"""Analise: números de reciclagem por bairro e por material (painel do admin)."""
from models.banco import rows


class Analise:
    """Consultas de análise por localização sobre máquinas e depósitos."""

    @staticmethod
    def por_localizacao():
        """Máquinas, depósitos, itens, pontos e usuários por bairro, e itens por material."""
        por_bairro = rows("""
            SELECT m.bairro, COUNT(DISTINCT m.id) AS maquinas, COUNT(d.id) AS depositos,
                   COALESCE(SUM(d.quantidade), 0) AS itens, COALESCE(SUM(d.pontos), 0) AS pontos,
                   COUNT(DISTINCT d.usuario_id) AS usuarios
            FROM maquinas m LEFT JOIN depositos d ON d.maquina_id = m.id
            GROUP BY m.bairro ORDER BY itens DESC""")
        por_material = rows(
            "SELECT material, SUM(quantidade) AS itens FROM depositos GROUP BY material ORDER BY itens DESC")
        return {"por_bairro": por_bairro, "por_material": por_material}
