"""Validação de campos (JSON ou formulário) reaproveitada pelos Models."""
from models.erros import DadosInvalidos


def texto(d, campo, nome, obrigatorio=True, maximo=120):
    """Texto sem espaços nas pontas. Falha se faltar (quando obrigatório) ou passar de `maximo` caracteres."""
    v = str(d.get(campo) or "").strip()
    if obrigatorio and not v:
        raise DadosInvalidos(f"informe {nome}")
    if len(v) > maximo:
        raise DadosInvalidos(f"{nome} muito longo")
    return v


def opcao(d, campo, nome, opcoes):
    """Valor que precisa ser uma das `opcoes` (ex.: sexo, UF)."""
    v = str(d.get(campo) or "").strip()
    if v not in opcoes:
        raise DadosInvalidos(f"escolha {nome}")
    return v
