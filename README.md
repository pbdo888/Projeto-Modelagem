# McCrea (protótipo)

**Repositório:** https://github.com/pbdo888/Projeto-Modelagem

Máquinas de reciclagem espalhadas pela cidade, pontos por item reciclado e cupons de marcas parceiras.
Stack: Python (Flask) + SQLite + mapas gratuitos (front em HTML/JS puro):
[MapLibre GL JS](https://maplibre.org/) para desenhar o mapa, [OpenFreeMap](https://openfreemap.org/) para as
imagens do mapa (dados do OpenStreetMap), [Nominatim](https://nominatim.org/) para transformar endereço em
latitude/longitude e [ViaCEP](https://viacep.com.br/) para preencher o endereço pelo CEP. Nenhum deles pede chave
nem cartão.

## Requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)

## Como rodar

1. Coloque os arquivos na mesma pasta e instale as dependências: `pip install -r requirements.txt`
2. Crie um arquivo `.env` ao lado do `app.py`:

   ```
   ADMIN_TOKEN=escolha-um-token
   SECRET_KEY=um-texto-aleatorio-longo
   ```

   **Variáveis de ambiente:**
   - `SECRET_KEY`: assina o cookie de login; sem ela, todos são deslogados a cada reinício do servidor
   - `ADMIN_TOKEN`: token para acessar rotas protegidas (painel de admin, criar máquinas/cupons)
   
   O mapa não precisa de chave (a antiga `GOOGLE_MAPS_API_KEY` não é mais usada).

3. Rode `python app.py` (o da raiz do projeto) e abra http://localhost:5050

O banco `mccrea.db` é criado e populado com dados de exemplo (São Paulo) na primeira execução.
Para recriá-lo, apague o arquivo. Para entrar, use por exemplo `ana@exemplo.com` com a senha `mccrea`
(senha de todos os usuários de exemplo). Contas antigas, criadas só com e-mail, completam o cadastro em
"Criar conta" com o mesmo e-mail e mantêm os pontos.

### Compartilhar com o professor

**Nota importante:** `localhost:5050` só funciona na sua máquina. Para o professor acessar, escolha uma opção:

#### Opção 1: Usar o IP local (mesma rede/WiFi)
```powershell
ipconfig
```
Procure pelo IPv4 (ex: `192.168.1.100`). O professor acessa: `http://192.168.1.100:5050`
- ✅ Simples
- ⚠️ Sua máquina precisa estar ligada com Flask rodando

#### Opção 2: Usar ngrok (acesso remoto temporário)
```bash
pip install ngrok
ngrok http 5050
```
Ele fornecerá um link público (ex: `https://abcd-1234-efgh.ngrok.io`)
- ✅ Funciona de qualquer lugar do mundo
- ⚠️ Link muda a cada execução
- ⚠️ Sua máquina precisa estar ligada

#### Opção 3: Deploy na Render (acesso permanente)
O repositório já tem `render.yaml` (Blueprint). Na Render: **New > Blueprint**, escolha este
repositório e confirme. O `SECRET_KEY` e o `ADMIN_TOKEN` são gerados automaticamente; para ver o
token do admin, abra o serviço > **Environment**. Cada push no `main` faz um novo deploy.
- ✅ Link fixo `https://<nome>.onrender.com`, sem precisar da sua máquina ligada
- ⚠️ Plano free: dorme após 15 min sem acesso (o primeiro acesso leva ~1 min) e o disco é
  apagado a cada deploy/reinício, então cadastros, pontos e cartazes enviados voltam aos dados de demonstração

### Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Os testes (pytest, formato AAA) passam por todas as rotas, como o navegador faria. Cada teste cria o app
numa pasta temporária com banco próprio, então o `mccrea.db` de verdade nunca é tocado.

## Estrutura (MVC)

O código segue o padrão **MVC** (Model-View-Controller). Uma requisição faz este caminho:

```
navegador ──▶ controller (rota) ──▶ model (regras + banco) ──▶ controller ──▶ JSON ou view (HTML)
```

- `app.py`: ponto de entrada; `criar_app()` junta configuração, rotas, banco e planilha (`python app.py` ou `gunicorn app:app`)
- `config.py`: configuração lida do ambiente / `.env` (`SECRET_KEY`, `ADMIN_TOKEN`, cookies, limite de upload)

**Models (`models/`)**: regras de negócio, acesso ao SQLite e manipulação de dados. Não conhecem HTTP: recebem
dados comuns e devolvem dados, ou levantam um erro de negócio que o controller transforma na resposta.
- `banco.py`: conexão por requisição, esquema (usuarios, funcionarios, maquinas, cupons, depositos, resgates, coletas, anuncios), migração e criação do banco
- `dados_exemplo.py`: dados de demonstração e os 13 cartazes iniciais (entram só num banco novo)
- `regras.py`: pontos por material e distância até a máquina
- `erros.py`: erros de negócio (`DadosInvalidos`, `NaoAutenticado`, `NaoEncontrado`, `Conflito`)
- `validacao.py`: validação de campos de texto e de opções
- `usuario.py` (`Usuario`): cadastro, login, endereço fixo e progresso nas fases do mapa de cupons
- `maquina.py` (`Maquina`): máquinas ativas, cadastro e as mais próximas de um ponto
- `deposito.py` (`Deposito`): leitura da máquina que vira pontos
- `cupom.py` (`Cupom`): cupons das marcas parceiras e resgate com pontos
- `anuncio.py` (`Anuncio`): notícias do carrossel e arquivos de cartaz
- `analise.py` (`Analise`): números por bairro e por material
- `planilha.py` (`Planilha`): gera `planilhas/usuarios.xlsx` a partir do banco (também roda sozinha, da raiz do projeto: `python -m models.planilha`)

**Views (`views/` e `static/`)**: o front-end, entregue pelos controllers
- `views/casa.html`: a Home (praça com as máquinas McCrea, carrossel de anúncios e Banco de Cupons)
- `views/index.html`: o app (menu de blocos estilo Wii U: notícias, mapa, fases, conta e admin; diálogos de login/cadastro)
- `views/admin_painel.html`: painel de administração, protegido por token
- `static/css/mccrea.css`: visual (vidro, blocos, botões táteis), mundo de cupons e transições entre telas
- `static/js/movimento.js`: curvas de animação, avisos e diálogos que abrem a partir do botão de origem (respeita `prefers-reduced-motion`)
- `static/js/mundo.js`: mundo de cupons no estilo do mapa do Super Mario Bros. Wii (fases, caminho e avatar)
- `static/js/app.js`: navegação entre telas (`#/inicio`, `#/mapa`, `#/fases`…), conta, mapa, notícias e painel de admin
- `static/cartazes/`: cartazes iniciais do carrossel de Notícias (slides da apresentação McCrea)
- `uploads/anuncios/`: cartazes enviados pelo painel de admin (fora do git)

**Controllers (`controllers/`)**: recebem a requisição, chamam o Model e respondem com JSON ou com uma View
- `__init__.py`: tabela de rotas (URL → controller), com os mesmos nomes de endpoint usados pelas views em `url_for()`
- `autenticacao.py`: `@requer_admin` (header `X-Admin-Token`) e `@requer_login` (cookie de sessão)
- `respostas.py`: respostas de erro `{"erro": ...}` e a tradução dos erros de negócio para 400/401/404/409/413
- `paginas_controller.py` (`/` e `/app`), `conta_controller.py`, `maquinas_controller.py`, `depositos_controller.py`,
  `cupons_controller.py`, `anuncios_controller.py` e `admin_controller.py` (painel, planilha e análise)

**Outros**
- `tests/`: testes das rotas (pytest, formato AAA)
- `prototipo/mundo-cupons.html`: protótipo do mundo de cupons com dados simulados (abre direto no navegador)
- `requirements.txt`: dependências Python do projeto; `requirements-dev.txt`: as mesmas + pytest

## Pontos principais

- Cadastro: `POST /api/cadastro` (nome, e-mail, senha, nascimento, sexo, estado civil, telefone, moradores,
  endereço fixo com lat/lng, aceite dos termos). Login: `POST /api/login`; sair: `POST /api/logout` (cookie de sessão)
- Endereço fixo: a máquina mais próxima é calculada a partir da casa do usuário, sem localização em tempo real.
  Alterar: `POST /api/eu/endereco`
- Máquina mais próxima: `GET /api/maquinas/proximas?lat=&lng=` (distância euclidiana em lat/lng, convertida para km)
- Progresso do usuário logado: `GET /api/eu` (fases do mapa de cupons e pontos que faltam)
- **Planilha automática:** `planilhas/usuarios.xlsx` é **gerada automaticamente** a partir do banco de dados:
  - Atualiza-se a cada: novo cadastro, mudança de endereço, nova máquina adicionada
  - Contém: ID, nome, email, telefone, endereço, localização, máquina mais próxima, saldo de pontos, depósitos
  - Cálculo automático: idade (a partir da data de nascimento), distância para máquina mais próxima em km
  - ⚠️ Se estiver aberta no Excel, a gravação falha (aviso no terminal) e é refeita na próxima vez
  - Pode ser baixada manualmente via painel de admin: `GET /api/admin/planilha`
- **Admin (header `X-Admin-Token`):** rotas protegidas para gerenciar o sistema
  - `POST /api/maquinas`: adicionar nova máquina
  - `POST /api/cupons`: criar cupom de parceira
  - `POST /api/depositos`: registrar depósito de material
  - `GET /api/analise`: análise de dados por localização
  - `GET /api/admin/painel`: interface do painel de admin (HTML)
  - `GET /api/admin/planilha`: baixar planilha de usuários
  - `GET /api/admin/anuncios`: todos os anúncios (inclusive ocultos)
  - `POST /api/anuncios`, `PUT /api/anuncios/<id>`, `DELETE /api/anuncios/<id>`: criar, editar e excluir anúncios
    (multipart: `imagem`, `titulo`, `texto`, `ordem`, `ativo`; imagem PNG/JPG/WebP/GIF até 5 MB, conferida pelo conteúdo)
- **Notícias (público):** `GET /api/anuncios` lista os anúncios publicados (carrossel) e `GET /api/anuncios/<id>`
  traz um anúncio completo ("Saiba mais"). Os 13 slides da apresentação entram como cartazes iniciais na criação da tabela

## Análise por localização

```python
import sqlite3, pandas as pd

df = pd.read_sql(
    "SELECT d.*, m.bairro, m.lat, m.lng FROM depositos d JOIN maquinas m ON m.id = d.maquina_id",
    sqlite3.connect("mccrea.db"))
print(df.groupby("bairro")[["quantidade", "pontos"]].sum())
```

## Dados e Segurança

### Arquivo `.gitignore`
Certifique-se de que `.gitignore` contém:
```
.env
mccrea.db
planilhas/usuarios.xlsx
.idea/
__pycache__/
*.pyc
```

Assim, dados sensíveis e arquivos gerados não são commitados.

### Proteção de dados pessoais (LGPD)
- A planilha `planilhas/usuarios.xlsx` contém dados pessoais
- **Nunca** compartilhe ou publique esse arquivo publicamente
- Para apresentações, use dados de exemplo ou dados anonimizados

## Limitações do protótipo

- Sem recuperação de senha nem limite de tentativas de login
- O Nominatim aceita no máximo 1 consulta por segundo e às vezes acha só a rua, sem o número; por isso o
  pino do cadastro pode ser arrastado. Com muitos cadastros, troque por um geocodificador com plano gratuito
  maior (LocationIQ, Geoapify) ou hospede o próprio Nominatim
- A leitura da máquina (infravermelho + visão computacional) é simulada: `POST /api/depositos` recebe material e quantidade
- Dados, bairros e marcas parceiras de exemplo são fictícios
- Sem autenticação em duas fatores
- Sem rate limiting (limite de requisições por IP)
