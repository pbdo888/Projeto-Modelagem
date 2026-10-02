"""Planilha de usuários (Excel). É regerada a cada cadastro ou mudança de endereço."""
import os
import sqlite3
from datetime import date, datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from db import DB_PATH, dist_km

PLANILHA_PATH = os.path.join("planilhas", "usuarios.xlsx")

COLUNAS = [  # (título, largura)
    ("ID", 6), ("Nome", 26), ("E-mail", 30), ("Telefone", 16), ("Nascimento", 12), ("Idade", 7),
    ("Sexo", 14), ("Estado civil", 16), ("Moradores", 10), ("CEP", 11), ("Logradouro", 30),
    ("Número", 8), ("Complemento", 14), ("Bairro", 18), ("Cidade", 16), ("UF", 5),
    ("Latitude", 11), ("Longitude", 11), ("Máquina mais próxima", 26), ("Distância (km)", 13),
    ("Saldo de pontos", 14), ("Pontos acumulados", 16), ("Depósitos", 10), ("Aceita ofertas", 13),
    ("Como conheceu", 20), ("Cadastro completo", 16), ("Cadastrado em", 18),
]


def idade(nascimento):
    if not nascimento:
        return None
    n = date.fromisoformat(nascimento)
    hoje = date.today()
    return hoje.year - n.year - ((hoje.month, hoje.day) < (n.month, n.day))


def gerar_planilha(caminho=PLANILHA_PATH):
    """Reescreve a planilha inteira a partir do banco. Grava num arquivo temporário e
    troca no fim, para nunca deixar uma planilha pela metade. Devolve False se o arquivo
    estiver aberto (o Excel bloqueia a gravação no Windows); a próxima geração tenta de novo."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    maquinas = con.execute("SELECT nome, lat, lng FROM maquinas WHERE status = 'ativa'").fetchall()
    usuarios = con.execute("""
        SELECT u.*, COALESCE(SUM(d.pontos), 0) AS acumulados, COUNT(d.id) AS n_depositos
        FROM usuarios u LEFT JOIN depositos d ON d.usuario_id = u.id
        GROUP BY u.id ORDER BY u.id""").fetchall()
    con.close()

    wb = Workbook()
    ws = wb.active
    ws.title = "Usuários"
    ws.append([t for t, _ in COLUNAS])
    for u in usuarios:
        maq, dist = None, None
        if u["lat"] is not None and maquinas:
            m = min(maquinas, key=lambda m: dist_km(u["lat"], u["lng"], m["lat"], m["lng"]))
            maq, dist = m["nome"], round(dist_km(u["lat"], u["lng"], m["lat"], m["lng"]), 2)
        ws.append([
            u["id"], u["nome"], u["email"], u["telefone"],
            date.fromisoformat(u["nascimento"]) if u["nascimento"] else None, idade(u["nascimento"]),
            u["sexo"], u["estado_civil"], u["moradores"], u["cep"], u["logradouro"], u["numero"],
            u["complemento"], u["bairro"], u["cidade"], u["uf"], u["lat"], u["lng"], maq, dist,
            u["pontos"], u["acumulados"], u["n_depositos"], "Sim" if u["aceita_ofertas"] else "Não",
            u["como_conheceu"], "Sim" if u["senha_hash"] and u["lat"] is not None else "Não",
            datetime.strptime(u["criado_em"], "%Y-%m-%d %H:%M:%S"),
        ])

    cabecalho = PatternFill("solid", fgColor="1AA3E8")
    for i, (_, largura) in enumerate(COLUNAS, start=1):
        c = ws.cell(row=1, column=i)
        c.font, c.fill = Font(bold=True, color="FFFFFF"), cabecalho
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = largura
    for linha in ws.iter_rows(min_row=2):
        linha[4].number_format = "DD/MM/YYYY"
        linha[26].number_format = "DD/MM/YYYY HH:MM"
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "C2"  # cabeçalho e nome sempre visíveis
    ws.auto_filter.ref = ws.dimensions

    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    tmp = caminho + ".tmp"
    wb.save(tmp)
    try:
        os.replace(tmp, caminho)
        return True
    except PermissionError:
        os.remove(tmp)
        return False


if __name__ == "__main__":
    print("Planilha gerada em", PLANILHA_PATH if gerar_planilha() else "(arquivo aberto, feche-o e rode de novo)")
