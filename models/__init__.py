"""
Models (o M do MVC): regras de negócio, acesso ao banco SQLite e manipulação de dados.

Os Models não conhecem HTTP (request, jsonify, códigos de status). Recebem dados comuns
(dicionários, arquivos enviados) e devolvem dados, ou levantam um erro de negócio
(models/erros.py) que o controller traduz para a resposta HTTP.

Os registros circulam como dicionários com as mesmas chaves das colunas do banco: é assim
que eles chegam ao JSON da API, exatamente como o front-end espera.

    banco.py          conexão, esquema das tabelas, migração e criação do banco
    dados_exemplo.py  dados de demonstração (máquinas, usuários, cupons, cartazes)
    regras.py         pontos por material e distância até a máquina
    erros.py          erros de negócio (dados inválidos, não encontrado, conflito...)
    validacao.py      validação de campos de texto e de opções
    usuario.py        Usuario: cadastro, login, endereço fixo, progresso nas fases
    maquina.py        Maquina: listar, criar, mais próximas
    deposito.py       Deposito: leitura da máquina que vira pontos
    cupom.py          Cupom: listar, criar, resgatar
    anuncio.py        Anuncio: notícias do carrossel e arquivos de cartaz
    analise.py        Analise: números por bairro e por material
    planilha.py       Planilha: planilhas/usuarios.xlsx gerada a partir do banco
"""
