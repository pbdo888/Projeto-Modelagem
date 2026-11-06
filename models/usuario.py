"""Usuario: cadastro, login, endereço fixo e progresso no mapa de cupons."""
import math
import re
from datetime import date

from werkzeug.security import check_password_hash, generate_password_hash

from models.banco import get_db, one, rows
from models.erros import Conflito, DadosInvalidos, NaoAutenticado
from models.planilha import Planilha
from models.regras import PONTOS_ITEM_MEDIO
from models.validacao import opcao, texto


class Usuario:
    """Pessoa cadastrada no McCrea (tabela usuarios). Os registros circulam como dicionários."""

    # Opções do cadastro (a View monta os <select> a partir destas listas)
    SEXOS = ["Feminino", "Masculino", "Outro", "Prefiro não informar"]
    ESTADOS_CIVIS = ["Solteiro(a)", "Casado(a)", "União estável", "Divorciado(a)", "Viúvo(a)", "Prefiro não informar"]
    COMO_CONHECEU = ["Redes sociais", "Indicação de amigo", "Vi uma máquina na rua", "Notícia ou imprensa", "Outro"]
    UFS = ["AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR",
           "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"]
    IDADE_MINIMA = 13

    @staticmethod
    def buscar(uid):
        """O usuário com esse id (linha completa da tabela), ou None."""
        return one("SELECT * FROM usuarios WHERE id = ?", (uid,))

    @staticmethod
    def publico(u):
        """Dados do usuário que podem ir para o navegador (nunca o hash da senha)."""
        return {k: v for k, v in u.items() if k != "senha_hash"}

    @classmethod
    def validar_endereco(cls, d):
        """Endereço fixo (base para a máquina mais próxima): CEP, rua, número, bairro, cidade, UF e lat/lng."""
        cep = re.sub(r"\D", "", str(d.get("cep") or ""))
        if len(cep) != 8:
            raise DadosInvalidos("CEP inválido (8 dígitos)")
        try:
            lat, lng = float(d["lat"]), float(d["lng"])
        except (KeyError, ValueError, TypeError):
            raise DadosInvalidos("localize o endereço no mapa antes de continuar")
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            raise DadosInvalidos("coordenadas inválidas")
        return {
            "cep": f"{cep[:5]}-{cep[5:]}",
            "logradouro": texto(d, "logradouro", "a rua"),
            "numero": texto(d, "numero", "o número", maximo=10),
            "complemento": texto(d, "complemento", "o complemento", obrigatorio=False, maximo=60),
            "bairro": texto(d, "bairro", "o bairro", maximo=60),
            "cidade": texto(d, "cidade", "a cidade", maximo=60),
            "uf": opcao(d, "uf", "o estado (UF)", cls.UFS),
            "lat": lat, "lng": lng,
        }

    @classmethod
    def validar_cadastro(cls, d):
        """Confere o cadastro completo e devolve as colunas prontas para gravar (senha já com hash)."""
        email = str(d.get("email") or "").strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            raise DadosInvalidos("e-mail inválido")
        senha = str(d.get("senha") or "")
        if len(senha) < 6:
            raise DadosInvalidos("a senha precisa ter pelo menos 6 caracteres")
        try:
            nasc = date.fromisoformat(str(d.get("nascimento")))
        except ValueError:
            raise DadosInvalidos("data de nascimento inválida")
        hoje = date.today()
        anos = hoje.year - nasc.year - ((hoje.month, hoje.day) < (nasc.month, nasc.day))
        if anos < cls.IDADE_MINIMA or anos > 120:
            raise DadosInvalidos(f"é preciso ter pelo menos {cls.IDADE_MINIMA} anos para se cadastrar")
        tel = re.sub(r"\D", "", str(d.get("telefone") or ""))
        if len(tel) not in (10, 11):
            raise DadosInvalidos("telefone inválido (DDD + número)")
        try:
            moradores = int(d.get("moradores"))
        except (TypeError, ValueError):
            raise DadosInvalidos("informe quantas pessoas moram na sua casa")
        if not 1 <= moradores <= 30:
            raise DadosInvalidos("número de moradores inválido")
        como = str(d.get("como_conheceu") or "").strip()
        if como and como not in cls.COMO_CONHECEU:
            raise DadosInvalidos("opção inválida em 'como conheceu'")
        if d.get("aceite_termos") is not True:
            raise DadosInvalidos("é preciso aceitar os termos de uso e a política de privacidade")
        return {
            "nome": texto(d, "nome", "o nome completo"),
            "email": email,
            "senha_hash": generate_password_hash(senha),
            "nascimento": nasc.isoformat(),
            "sexo": opcao(d, "sexo", "o sexo", cls.SEXOS),
            "estado_civil": opcao(d, "estado_civil", "o estado civil", cls.ESTADOS_CIVIS),
            "telefone": f"({tel[:2]}) {tel[2:-4]}-{tel[-4:]}",
            "moradores": moradores,
            "como_conheceu": como or None,
            "aceita_ofertas": 1 if d.get("aceita_ofertas") else 0,
            **cls.validar_endereco(d),
        }

    @classmethod
    def cadastrar(cls, d):
        """Cria a conta e devolve o id. Conta antiga (só e-mail, sem senha) é completada e mantém os pontos."""
        dados = cls.validar_cadastro(d)
        con = get_db()
        existente = one("SELECT id, senha_hash FROM usuarios WHERE email = ?", (dados["email"],))
        if existente and existente["senha_hash"]:
            raise Conflito("este e-mail já tem cadastro; use Entrar")
        cols = list(dados)
        if existente:  # conta antiga (só e-mail, sem senha): completa o cadastro e mantém os pontos
            con.execute(f"UPDATE usuarios SET {', '.join(c + ' = ?' for c in cols)}, aceite_termos_em = CURRENT_TIMESTAMP "
                        "WHERE id = ?", [*dados.values(), existente["id"]])
            uid = existente["id"]
        else:
            uid = con.execute(f"INSERT INTO usuarios ({', '.join(cols)}, aceite_termos_em) "
                              f"VALUES ({', '.join('?' * len(cols))}, CURRENT_TIMESTAMP)", list(dados.values())).lastrowid
        con.commit()
        Planilha.atualizar()
        return uid

    @staticmethod
    def autenticar(d):
        """Confere e-mail e senha e devolve o usuário (linha completa)."""
        email, senha = str(d.get("email", "")).strip().lower(), str(d.get("senha", ""))
        u = one("SELECT * FROM usuarios WHERE email = ?", (email,))
        if u and not u["senha_hash"]:
            raise Conflito("conta antiga: finalize seu cadastro para criar uma senha")
        if not u or not check_password_hash(u["senha_hash"], senha):
            raise NaoAutenticado("e-mail ou senha incorretos")
        return u

    @classmethod
    def mudar_endereco(cls, uid, d):
        """Troca o endereço fixo do usuário (a máquina mais próxima é calculada a partir dele)."""
        end = cls.validar_endereco(d)
        con = get_db()
        con.execute(f"UPDATE usuarios SET {', '.join(c + ' = ?' for c in end)} WHERE id = ?", [*end.values(), uid])
        con.commit()
        Planilha.atualizar()

    @classmethod
    def progresso(cls, u):
        """Pontos e fases do mapa de cupons.

        Mapa de fases: cada cupom ativo é uma fase, em ordem de custo. A fase é liberada pelos
        pontos acumulados (soma dos depósitos), que nunca diminuem; assim o avatar não volta
        no mapa quando o usuário resgata um cupom. O resgate continua gastando o saldo (pontos)."""
        uid = u["id"]
        total = one("SELECT COALESCE(SUM(pontos), 0) AS t FROM depositos WHERE usuario_id = ?", (uid,))["t"]
        resgates = {r["cupom_id"]: r["n"] for r in rows(
            "SELECT cupom_id, COUNT(*) AS n FROM resgates WHERE usuario_id = ? GROUP BY cupom_id", (uid,))}
        fases = [dict(c, fase=i + 1, liberada=total >= c["custo"], resgatavel=u["pontos"] >= c["custo"],
                      resgates=resgates.get(c["id"], 0))
                 for i, c in enumerate(rows("SELECT * FROM cupons WHERE ativo = 1 ORDER BY custo, id"))]
        prox = next((f for f in fases if not f["liberada"]), None)
        faltam = prox["custo"] - total if prox else 0
        return {
            "usuario": cls.publico(u), "pontos_totais": total, "fases": fases,
            "fase_atual": sum(f["liberada"] for f in fases),  # 0 = ainda no início do mapa
            "proximo_cupom": prox, "faltam_pontos": faltam,
            "faltam_itens": math.ceil(faltam / PONTOS_ITEM_MEDIO),
        }
