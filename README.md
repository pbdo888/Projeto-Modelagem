# ReciclaVerde (protótipo)

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

3. Rode `python app.py` e abra http://localhost:5000

O banco `reciclaverde.db` é criado e populado com dados de exemplo (São Paulo) na primeira execução.
Para recriá-lo, apague o arquivo. Para entrar, use por exemplo `ana@exemplo.com` com a senha `reciclaverde`
(senha de todos os usuários de exemplo). Contas antigas, criadas só com e-mail, completam o cadastro em
"Criar conta" com o mesmo e-mail e mantêm os pontos.

### Compartilhar com o professor

**Nota importante:** `localhost:5000` só funciona na sua máquina. Para o professor acessar, escolha uma opção:

#### Opção 1: Usar o IP local (mesma rede/WiFi)
```powershell
ipconfig
```
Procure pelo IPv4 (ex: `192.168.1.100`). O professor acessa: `http://192.168.1.100:5000`
- ✅ Simples
- ⚠️ Sua máquina precisa estar ligada com Flask rodando

#### Opção 2: Usar ngrok (acesso remoto temporário)
```bash
pip install ngrok
ngrok http 5000
```
Ele fornecerá um link público (ex: `https://abcd-1234-efgh.ngrok.io`)
- ✅ Funciona de qualquer lugar do mundo
- ⚠️ Link muda a cada execução
- ⚠️ Sua máquina precisa estar ligada

#### Opção 3: Deploy em servidor (acesso permanente)
Hospede em Heroku, AWS, Replit ou similar. Mais profissional, mas requer configuração adicional.

## Estrutura

- `db.py`: esquema (usuarios, funcionarios, maquinas, cupons, depositos, resgates, coletas), migração e dados de exemplo
- `app.py`: API REST e rota da página (Flask)
- `planilha.py`: gera `planilhas/usuarios.xlsx` a partir do banco de dados (também roda sozinho: `python planilha.py`)
- `index.html`: mapa interativo, cadastro/login, mundo de cupons
- `admin_painel.html`: painel de administração, protegido por token
- `requirements.txt`: dependências Python do projeto

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

## Análise por localização

```python
import sqlite3, pandas as pd

df = pd.read_sql(
    "SELECT d.*, m.bairro, m.lat, m.lng FROM depositos d JOIN maquinas m ON m.id = d.maquina_id",
    sqlite3.connect("reciclaverde.db"))
print(df.groupby("bairro")[["quantidade", "pontos"]].sum())
```

## Dados e Segurança

### Arquivo `.gitignore`
Certifique-se de que `.gitignore` contém:
```
.env
reciclaverde.db
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
