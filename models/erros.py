"""
Erros de negócio levantados pelos Models.

O Model não conhece HTTP: ele só diz O QUE deu errado, com a mensagem que vai para a tela.
Quem transforma cada tipo de erro em código HTTP (400, 401, 404, 409) é o controller
(controllers/respostas.py).
"""


class ErroDeNegocio(Exception):
    """Base: uma regra do McCrea impediu a operação. A mensagem é mostrada ao usuário."""


class DadosInvalidos(ErroDeNegocio, ValueError):
    """Dados incompletos ou fora das regras (vira 400 Bad Request)."""


class NaoAutenticado(ErroDeNegocio):
    """E-mail ou senha não conferem (vira 401 Unauthorized)."""


class NaoEncontrado(ErroDeNegocio):
    """O registro pedido não existe (vira 404 Not Found)."""


class Conflito(ErroDeNegocio):
    """A operação esbarra no estado atual: e-mail já cadastrado, máquina cheia,
    pontos insuficientes... (vira 409 Conflict)."""
