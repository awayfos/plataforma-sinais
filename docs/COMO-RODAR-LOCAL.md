# Como rodar a plataforma no seu computador

Guia do zero até ver o terminal com o gráfico ao vivo. Leva uns 15 minutos na primeira vez (a maior parte é o Docker baixando imagens e o histórico de preços sendo baixado da Binance).

O que vai rodar:

| Parte | Onde roda | Endereço |
|---|---|---|
| Banco (PostgreSQL + TimescaleDB), Redis, coletor de candles, serviço de ticks, motor de análise e API | Docker (um comando) | API em `http://localhost:8000` |
| Site (Next.js) | Node.js no seu terminal | `http://localhost:3000` |

> Use sempre **`localhost`** no navegador, nunca `127.0.0.1` nem o IP da máquina. O login grava o cookie da sessão para o endereço em que você entrou; com outro endereço o navegador não manda o cookie, a conexão ao vivo é recusada e a tela fica voltando para o login.

## 1. O que instalar antes

- **Git** — para baixar o repositório.
- **Docker** com o **Docker Compose v2** (o comando é `docker compose`, com espaço):
  - Linux: Docker Engine + plugin compose.
  - macOS: Docker Desktop.
  - Windows: veja a seção 9 (precisa de WSL 2).
- **Node.js 22** (mínimo 20.9) com o `npm`.
- Um **aplicativo autenticador** no celular (Google Authenticator, Microsoft Authenticator, Authy, 1Password…), para o 2FA do administrador.

Confira:

```bash
git --version
docker compose version
node --version     # v22.x (ou ≥ 20.9)
```

## 2. Baixar o repositório

```bash
git clone https://github.com/awayfos/plataforma-sinais.git
cd plataforma-sinais
```

Todos os comandos abaixo são rodados **a partir da pasta `plataforma-sinais`**, salvo quando diz `cd frontend`.

## 3. Configuração (`.env`)

O `infra/dev.sh` cria o `.env` sozinho na primeira vez (passo 4). Se preferir criar à mão:

```bash
cp .env.example .env
```

e, no `.env`, para o desenvolvimento:

- `SINAIS_HISTORICO_DIAS=3` (o padrão de 730 dias leva horas para baixar; 3 dias bastam para ver tudo funcionando);
- `SINAIS_HISTORICO_DIAS_1S=1`.

O resto já vem pronto para o desenvolvimento:

- `SINAIS_CHAVE_CIFRA` do `.env.example` é **só para desenvolvimento** (a configuração de produção recusa);
- `SINAIS_ORIGENS_PERMITIDAS=http://localhost:3000` (o endereço do site);
- `SINAIS_COOKIE_SEGURO=true`: Chrome, Edge e Firefox aceitam cookies `Secure` em `http://localhost`. Se usar **Safari** e o login não "pegar", troque para `false` (só no desenvolvimento — nunca em produção, que recusa).

Sempre que rodar o Docker Compose à mão, passe o arquivo: `docker compose -f infra/docker-compose.yml --env-file .env …` (o `infra/dev.sh` já faz isso).

## 4. Subir o backend

```bash
infra/dev.sh subir
```

O script:

1. cria o `.env` a partir do `.env.example` se ele não existir (com 3 dias de histórico);
2. constrói as imagens e sobe `db`, `redis`, `migracoes` (cria as tabelas), `coletor`, `ticks`, `motor_analise` e `api`;
3. espera a API responder e mostra o estado.

Outros comandos úteis:

```bash
infra/dev.sh status          # serviços e quantos candles de 1 min já estão no banco
infra/dev.sh logs coletor    # acompanha o download do histórico (Ctrl+C para sair)
infra/dev.sh logs api        # logs da API
infra/dev.sh parar           # para tudo (os dados ficam)
infra/dev.sh apagar          # para e APAGA o banco (recomeça do zero)
```

O histórico continua baixando em segundo plano. O gráfico já funciona com o que tiver chegado; a análise aparece no primeiro minuto fechado depois que o motor carregou os dados (até lá o painel mostra "Análise ainda não disponível para este ativo.").

## 5. Criar o administrador (com 2FA)

```bash
infra/dev.sh admin voce@exemplo.com "Seu Nome"
```

- Ele pede a senha (mínimo de 10 caracteres). Para não digitar: `SINAIS_ADMIN_SENHA='sua-senha-longa' infra/dev.sh admin voce@exemplo.com "Seu Nome"`.
- A saída é uma linha `otpauth://totp/...secret=XXXX...`. No aplicativo autenticador, escolha **adicionar conta → inserir chave de configuração**, use o e-mail como nome da conta e cole o valor depois de `secret=` (até o próximo `&`), tipo "baseado em tempo". Também dá para gerar um QR code com a linha inteira.
- Essa linha é o segredo do 2FA: não compartilhe. Rodar o comando de novo para o mesmo e-mail **redefine** a senha e o segredo (o autenticador antigo deixa de valer).

## 6. Subir o site

Em outro terminal:

```bash
cd frontend
npm ci
npm run dev
```

Abra **http://localhost:3000** e entre com o e-mail e a senha do admin; em seguida, digite o código de 6 dígitos do autenticador.

O site fala só com `/api` no próprio endereço; o Next repassa para a API em `http://127.0.0.1:8000` (isso é interno do servidor e não afeta o cookie). O WebSocket ao vivo também passa pelo Next (`ws://localhost:3000/api/ws`).

## 7. Criar um cliente (plano e assinatura)

O admin entra no terminal sem assinatura; um cliente precisa de plano e assinatura ativa:

1. **Admin → Planos**: crie um plano (nome, duração em dias, preço, ativos BTCUSDT/ETHUSDT, expirações, modo avançado).
2. **Admin → Usuários → Novo usuário**: e-mail, nome, senha temporária (≥ 10 caracteres) e o plano. A assinatura é criada junto (vence pela duração do plano, ou na data informada).
3. Saia e entre como o cliente (em outra janela anônima, para manter o admin aberto). O cliente não precisa de 2FA.
4. Para renovar: **Renovar** na linha do usuário (ou **Admin → Assinaturas**). Para cortar o acesso na hora: **Encerrar** (pede confirmação).

## 8. O que esperar e problemas comuns

- **Sinais em "AGUARDAR" em todas as expirações**: é o esperado. Nenhum modelo foi aprovado na validação (ver `docs/PROGRESSO.md`); a plataforma não mostra sinal que não passou.
- **Gráfico parado / "Ao vivo indisponível"**: confira `infra/dev.sh logs ticks` (precisa de acesso à internet para a Binance) e se você abriu `localhost`, não `127.0.0.1`.
- **Volta sempre para o login**: endereço diferente de `localhost`, ou Safari com cookie `Secure` (use `SINAIS_COOKIE_SEGURO=false` no `.env` e rode `infra/dev.sh subir` de novo).
- **Conexão ao vivo recusada (4403)**: o site está em outro endereço/porta. Inclua-o em `SINAIS_ORIGENS_PERMITIDAS` no `.env` (separado por vírgula) e rode `infra/dev.sh subir`.
- **"Código do autenticador inválido"**: o relógio do celular ou do computador está errado (o código vale 30 s), ou o mesmo código já foi usado — espere o próximo.
- **Bloqueado após erros de senha**: o bloqueio dura de 1 a 30 min por endereço. O navegador em que você já entrou antes continua podendo entrar mesmo sob ataque distribuído (cookie "dispositivo confiável").
- **Erro da Binance REST (HTTP 451) no coletor**: a `api.binance.com` bloqueia algumas regiões. Use `SINAIS_BINANCE_REST_URL=https://data-api.binance.vision` no `.env` (é o que o CI usa).
- **Portas ocupadas (5432, 6379, 8000, 3000)**: pare o outro programa ou o PostgreSQL/Redis instalado na máquina.

## 9. Windows (o computador do cliente)

O backend roda em contêineres Linux, então no Windows ele depende do **Docker Desktop**, que por sua vez precisa do **WSL 2**. Não dá para garantir que funcione em qualquer Windows; antes de tentar, confira:

- **Versão do Windows**: Windows 10 64 bits 22H2 ou Windows 11 64 bits **atualizado** (o Docker Desktop atual pede uma versão suportada pela Microsoft; um Windows 11 muito desatualizado precisa primeiro do Windows Update).
- **Virtualização ligada** na BIOS/UEFI (Intel VT-x ou AMD-V) — no Gerenciador de Tarefas → Desempenho → CPU aparece "Virtualização: Habilitado".
- **Memória**: 8 GB de RAM no mínimo (16 GB recomendado); uns 20 GB livres em disco.

Caminho sugerido:

1. Atualizar o Windows (Windows Update) até não haver pendências.
2. No PowerShell como administrador: `wsl --install` e reiniciar. Isso instala o WSL 2 e um Ubuntu.
3. Instalar o Docker Desktop e, nas configurações, deixar marcado "Use the WSL 2 based engine" e a integração com o Ubuntu.
4. Abrir o **Ubuntu** (no menu Iniciar) e seguir este guia **dentro dele** (passos 2 a 6), com o repositório clonado na pasta do Linux (`~/plataforma-sinais`, não em `C:\`): o `infra/dev.sh` é um script bash e o disco do Linux é bem mais rápido. Instale o Node.js 22 dentro do Ubuntu também.
5. O navegador do Windows abre `http://localhost:3000` normalmente (o WSL 2 repassa o `localhost`).

Se o Docker Desktop não instalar (Windows sem suporte ou sem virtualização), as alternativas são: atualizar o Windows; usar outro computador com Linux ou macOS; ou rodar o backend numa máquina virtual Linux/servidor na nuvem e apontar o site para ele (`SINAIS_API_URL=http://<servidor>:8000 npm run dev`, com o cuidado de que o cookie fica no endereço do site, `localhost:3000`, e a origem precisa estar em `SINAIS_ORIGENS_PERMITIDAS`). Nenhuma dessas alternativas foi testada no computador do cliente.

## 10. Testes (opcional)

```bash
# backend (precisa do uv: https://docs.astral.sh/uv/)
cd backend && uv sync && uv run pytest && uv run ruff check && uv run mypy

# frontend
cd frontend && npm ci && npm run lint && npm run typecheck && npm test
npm run build && npx playwright install chromium && npm run e2e
```

O CI roda tudo isso e ainda o teste ponta a ponta real (`e2e-real`: navegador → Next → API → Redis → Binance).
