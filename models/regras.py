"""Regras de negócio que não dependem do banco: quanto vale cada material e a distância até a máquina."""
import math

PONTOS_MATERIAL = {"pet": 10, "lata": 15, "vidro": 20, "papel": 5}  # pontos por item
PONTOS_ITEM_MEDIO = 10  # só para estimar "faltam N itens"


def dist_km(lat1, lng1, lat2, lng2):
    """Distância euclidiana no plano (lat, lng). Graus viram km: 1° ≈ 111,32 km,
    e a longitude é encolhida por cos(latitude) para não distorcer o resultado."""
    x = (lng2 - lng1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = lat2 - lat1
    return 111.32 * math.hypot(x, y)
