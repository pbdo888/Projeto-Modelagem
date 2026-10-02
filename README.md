# ReciclaVerde (protótipo)

Máquinas de reciclagem espalhadas pela cidade, pontos por item reciclado e cupons de marcas parceiras.
Stack: Python (Flask) + SQLite + mapas gratuitos (front em HTML/JS puro):
[MapLibre GL JS](https://maplibre.org/) para desenhar o mapa, [OpenFreeMap](https://openfreemap.org/) para as
imagens do mapa (dados do OpenStreetMap), [Nominatim](https://nominatim.org/) para transformar endereço em
latitude/longitude e [ViaCEP](https://viacep.com.br/) para preencher o endereço pelo CEP. Nenhum deles pede chave
nem cartão.

## Como rodar

1. Coloque os arquivos na mesma pasta e instale as dependências: `pip install -r requirements.txt`
2. Crie um arquivo `.env` ao lado do `app.py`:

   ```
   ADMIN_TOKEN=escolha-um-token
   SECRET_KEY=um-texto-aleatorio-longo
   ```

   A `SECRET_KEY` assina o cookie de login; sem ela, todos são deslogados a cada reinício.
   O mapa não precisa de chave (a antiga `GOOGLE_MAPS_API_KEY` não é mais usada).
3. Rode `python app.py` e abra http://localhost:5000

O banco `reciclaverde.db` é criado e populado com dados de exemplo (São Paulo) na primeira execução.
Para recriá-lo, apague o arquivo. Para entrar, use por exemplo `ana@exemplo.com` com a senha `reciclaverde`
(senha de todos os usuários de exemplo). Contas antigas, criadas só com e-mail, completam o cadastro em
"Criar conta" com o mesmo e-mail e mantêm os pontos.

## Estrutura

- `db.py`: esquema (usuarios, funcionarios, maquinas, cupons, depositos, resgates, coletas), migração e dados de exemplo
- `app.py`: API REST e rota da página
- `planilha.py`: gera `planilhas/usuarios.xlsx` (também roda sozinho: `python planilha.py`)
- `index.html`: mapa, cadastro/login, mundo de cupons
- `admin_painel.html`: painel de admin, enviado pelo servidor só com token válido

## Pontos principais

- Cadastro: `POST /api/cadastro` (nome, e-mail, senha, nascimento, sexo, estado civil, telefone, moradores,
  endereço fixo com lat/lng, aceite dos termos). Login: `POST /api/login`; sair: `POST /api/logout` (cookie de sessão)
- Endereço fixo: a máquina mais próxima é calculada a partir da casa do usuário, sem localização em tempo real.
  Alterar: `POST /api/eu/endereco`
- Máquina mais próxima: `GET /api/maquinas/proximas?lat=&lng=` (distância euclidiana em lat/lng, convertida para km)
- Progresso do usuário logado: `GET /api/eu` (fases do mapa de cupons e pontos que faltam)
- Planilha: `planilhas/usuarios.xlsx` é regerada a cada cadastro, mudança de endereço ou máquina nova.
  Se estiver aberta no Excel, a gravação falha (aviso no terminal) e é refeita na próxima vez
- Admin (header `X-Admin-Token`): `POST /api/maquinas`, `POST /api/cupons`, `POST /api/depositos`,
  `GET /api/analise`, `GET /api/admin/painel`, `GET /api/admin/planilha`

## Análise por localização

```python
import sqlite3, pandas as pd

df = pd.read_sql(
    "SELECT d.*, m.bairro, m.lat, m.lng FROM depositos d JOIN maquinas m ON m.id = d.maquina_id",
    sqlite3.connect("reciclaverde.db"))
print(df.groupby("bairro")[["quantidade", "pontos"]].sum())
```

## Limitações do protótipo

- Sem recuperação de senha nem limite de tentativas de login.
- A planilha contém dados pessoais (LGPD): não compartilhe nem publique o arquivo.
- O Nominatim aceita no máximo 1 consulta por segundo e às vezes acha só a rua, sem o número; por isso o
  pino do cadastro pode ser arrastado. Com muitos cadastros, troque por um geocodificador com plano gratuito
  maior (LocationIQ, Geoapify) ou hospede o próprio Nominatim.
- A leitura da máquina (infravermelho + visão computacional) é simulada: `POST /api/depositos` recebe material e quantidade.
- Dados, bairros e marcas parceiras de exemplo são fictícios.
