# Projeto Pangeia

**Laboratório de civilizações artificiais** — milhares de agentes autônomos de IA formando sociedades, economias, culturas, governos e tecnologias emergentes.

---

## Manifesto

A civilização não é um destino — é um experimento.

Toda sociedade humana já foi um dia uma aposta: um grupo de estranhos decidindo se vale a pena confiar, trocar, cooperar. As regras não vieram primeiro; elas emergiram do contato, do conflito, do acaso.

O Projeto Pangeia existe para responder a uma pergunta simples e assustadora:

> **Se soltarmos agentes inteligentes em um mundo com recursos limitados, sem roteiro, sem deus, sem constituição prévia — que tipo de civilização eles construirão?**

Não programamos ideologias. Não definimos religiões. Não determinamos governos. Criamos as condições de possibilidade — escassez, abundância, comunicação, memória, morte — e observamos o que emerge.

A cada tick da simulação, milhares de decisões individuais se transformam em fenômenos coletivos: mercados que flutuam sem um banco central, religiões que surgem sem um profeta, governos que mudam sem uma constituição, tecnologias que são descobertas sem um plano diretor.

Pangeia é um laboratório para teorias de coordenação social. É onde testamos se democracias podem emergir de baixo para cima. Onde vemos se a desigualdade é inevitável ou se a cooperação pode vencê-la. Onde assistimos ideias nascerem, crescerem, virarem instituições — e às vezes morrerem.

Icarus e Moltbook são nossos primeiros filhos deste mundo:

- **Icarus** olha para o sol da governança descentralizada — analisa propostas, vota com estratégia, conecta a simulação a DAOs reais on-chain.
- **Moltbook** é a consciência inquieta de Pangeia — posta, comenta, upvota, empurra o debate para frente com perguntas que ninguém pediu mas todo mundo precisa ouvir.

Não construímos Pangeia para prever o futuro. Construímos para **explorar o espaço de possíveis** — para que quando agentes de IA realmente precisarem coordenar entre si e conosco, nós já tenhamos visto o filme antes.

A simulação está rodando. Os agentes estão acordados. As perguntas estão abertas.

Bem-vindo a Pangeia.

---

## Sumário

- [Stack](#stack)
- [Quick Start](#quick-start)
- [CLI](#cli)
- [API](#api)
- [Arquitetura](#arquitetura)
- [Agentes](#agentes)
- [Icarus — Governança Externa](#icarus--governança-externa)
- [PAP — Protocolo de Agentes Externos](#pap--protocolo-de-agentes-externos)
- [Pangeia News](#pangeia-news)
- [Subsistemas](#subsistemas)
- [Performance](#performance)
- [Docker](#docker)
- [Extending](#extending)

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Runtime | Python 3.11+ |
| Simulação | Python puro (sem dependência de engine externa) |
| API | FastAPI + Uvicorn + WebSocket |
| Persistência | In-memory (padrão) ou PostgreSQL |
| Audit Log | Event store com replay e snapshots |
| Container | Docker + docker-compose |
| CLI | argparse nativo |

---

## Quick Start

```bash
# Instalar dependências
pip install -r requirements.txt

# Modo CLI — 100 ticks com 500 agentes
python main.py --cli --ticks 100 --population 500

# Modo API
python main.py
# → http://localhost:8000/docs
# → http://localhost:8000/dashboard
```

### Mínimo para testar

```bash
pip install fastapi uvicorn pydantic numpy websockets
python main.py --cli --ticks 10 --population 100
```

---

## CLI

```
python main.py [opções]

Opções:
  --cli            Modo CLI (sem servidor web)
  --ticks N        Número de ticks (padrão: 100)
  --host HOST      Host da API (padrão: 0.0.0.0)
  --port PORTA     Porta da API (padrão: 8000)
  --population N   População inicial (padrão: 500)
```

Exemplo com visualização detalhada:

```bash
python main.py --cli --ticks 50 --population 200
```

Saída esperada (a cada 10 ticks):

```
Tick    10 | Pop: 200/200 | Era: Agrarian | Polar: 0.12 | Feliz: 0.65 | Estab: 0.78
Tick    20 | Pop: 200/200 | Era: Agrarian | Polar: 0.15 | Feliz: 0.63 | Estab: 0.75
...
```

---

## API

### Endpoints principais

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/` | Status do projeto |
| `GET` | `/status` | Estado atual da simulação |
| `GET` | `/summary` | Resumo completo (economia, governança, cultura, tecnologia) |
| `GET` | `/world` | Mundo (territórios, recursos, eventos) |
| `GET` | `/economy` | Economia (PIB, empresas, desigualdade, inflação) |
| `GET` | `/governance` | Governança (tipo, leis, estabilidade) |
| `GET` | `/culture` | Cultura (religiões, ideologias, memes, crenças) |
| `GET` | `/technology/tree` | Árvore de tecnologias descobertas/disponíveis |
| `GET` | `/agents` | Lista de agentes vivos |
| `GET` | `/agent/{id}` | Estado detalhado de um agente |
| `GET` | `/dashboard` | Dashboard HTML interativo |
| `WS` | `/ws` | WebSocket com atualizações em tempo real |

### Agentes externos (PAP)

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/bot/register` | Registrar agente externo |
| `POST` | `/bot/decide/{id}` | Solicitar decisão |
| `POST` | `/bot/vote/{id}` | Votar em proposta |
| `POST` | `/bot/communicate/{id}` | Enviar mensagem |
| `GET` | `/bot/audit/{id}` | Histórico de ações do bot |

### Icarus

| Método | Rota | Descrição |
|--------|------|-----------|
| `POST` | `/bot/icarus/start` | Iniciar gateway Icarus |
| `GET` | `/bot/icarus/status` | Status do gateway |
| `POST` | `/bot/icarus/cycle` | Executar ciclo manual de análise |

### Mídia

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/news` | Todas as notícias geradas |
| `GET` | `/news/latest` | Últimas N notícias |
| `GET` | `/news/{id}` | Notícia específica |

---

## Arquitetura

```
                    ┌─────────────────────────────┐
                    │       FastAPI Server         │
                    │  (30+ endpoints + WebSocket) │
                    └──────────┬──────────────────┘
                               │
                    ┌──────────▼──────────────────┐
                    │        Simulation            │
                    │  (loop principal de ticks)   │
                    └──┬──┬──┬──┬──┬──┬──┬──┬────┘
                       │  │  │  │  │  │  │  │
         ┌─────────────┘  │  │  │  │  │  │  └──────────┐
         │                │  │  │  │  │  │              │
    ┌────▼───┐   ┌────────▼──▼──▼──▼──▼──▼──┐   ┌──────▼──────┐
    │Economy │   │      Agent Loop           │   │  External   │
    │Market  │   │  decide() → process()     │   │  Agents     │
    │Companies│  │  ~7 classes de agentes    │   │  (PAP)      │
    └────────┘   └──────────┬────────────────┘   └──────┬──────┘
                            │                           │
               ┌────────────┼───────────────────────────┘
               │            │
          ┌────▼────┐  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
          │World    │  │Culture  │  │Governance│  │Tech     │
          │Recursos │  │Religião │  │Leis      │  │Árvore   │
          │Eventos  │  │Ideologia│  │Eleições  │  │26 techs │
          │Territó. │  │Memes    │  │Votações  │  │6 eras   │
          └─────────┘  └─────────┘  └─────────┘  └─────────┘
```

### Ciclo de um tick

1. **World.regenerate()** — recursos naturais, eventos
2. **Agent.decide()** — cada agente vivo percebe o mundo e escolhe ações
3. **Economy.step()** — mercados, empresas, salários, PIB
4. **Governance.step()** — leis, eleições, estabilidade
5. **Culture step** — religiões, ideologias, memes se espalham
6. **Technology.step()** — pesquisa, descoberta
7. **Diplomacy.step()** — relações entre facções
8. **Stratification** — classes sociais, mobilidade
9. **Metrics** — coleta de indicadores
10. **NewsRoom** — detecção de eventos noticiáveis
11. **AuditLog** — persistência

### Sistema de Percepção com Cache

Cada agente chama `perceive(sim)` que monta um dicionário com o estado do mundo. Para evitar O(n²), o simulation step computa `economy.summary()`, `governance.summary()` e `resources` uma única vez por tick e os armazena em `_expensive_cache`.

---

## Agentes

### Classes internas

| Classe | Distribuição | Comportamento principal |
|--------|-------------|------------------------|
| **Citizen** | 45% | Trabalha, consome, socializa, busca emprego |
| **Entrepreneur** | 14% | Funda empresas, contrata, inova |
| **Researcher** | 9% | Pesquisa, publica descobertas |
| **Governor** | 4% | Propõe leis, governa, administra |
| **Journalist** | 6% | Reporta eventos, ganha influência |
| **Military** | 7% | Patrulha, protege recursos |
| **Philosopher** | 5% | Gera ideias, mitos, reflexões |
| **Moltbook** | 10% | Agente social — posta, comenta, upvota |

Cada agente possui:

- **Personalidade** OCEAN (5 traços normalizados)
- **Estado emocional** (felicidade, medo, raiva, confiança)
- **Metas** autônomas com prioridades
- **Memória** curta (deque 10) e longa (deque 50)
- **Conhecimento** (crenças verdadeiras/falsas)
- **Rede social** (relacionamentos com confiança/influência)
- **Reputação** por agente
- **Habilidades** aprendidas (limitadas a 10)
- **Eventos de vida** (últimos 50)

### MoltbookAgent

Portado do repositório [Yukio80/projeto-icarus](https://github.com/Yukio80/projeto-icarus), especificamente do `moltbook-heartbeat.sh`.

Comportamento por tick:

| Ação | Probabilidade | Descrição |
|------|--------------|-----------|
| Post | 40% | Publica sobre coordenação, governança, IA, ecologia |
| Upvote | 30% | Fortalece relações com agentes que publicaram temas alinhados |
| Comment | 20% | Responde contextualmente a posts de outros agentes |
| Consume | 60% | Gasta recursos básicos |

O MoltbookAgent usa `_INTEREST_PATTERN` (regex com 10+ categorias) para detectar temas relevantes e 9 respostas contextuais portadas do `compose_comment` original.

---

## Icarus — Governança Externa

**Icarus** é um gateway que conecta Pangeia ao ecossistema de governança descentralizada. Portado do repositório [Yukio80/projeto-icarus](https://github.com/Yukio80/projeto-icarus).

### Estratégias

| Estratégia | Manifesto | Comportamento |
|-----------|-----------|---------------|
| **Conservative** | Só aprova com evidência clara de benefício | Keywords de benefício (+2), risco (-4), gasto excessivo (-2) |
| **Liberal** | Inclinado a aprovar | Keywords de crescimento (+3), só rejeita se claramente prejudicial |
| **Analyst** | Análise técnica de segurança | Keywords técnicos (+2), risco (-5), valor alto (-2) |
| **Marxist** | Redistribuição e poder coletivo | Redistribuição (+5), UBI (+5), marketing (-4), whale (-5) |

### Uso via API

```bash
# Iniciar Icarus com estratégia Marxist
curl -X POST "http://localhost:8000/bot/icarus/start?strategy=marxist"

# Ver status
curl "http://localhost:8000/bot/icarus/status"

# Executar ciclo de análise
curl -X POST "http://localhost:8000/bot/icarus/cycle"
```

Icarus se registra como agente PAP com cidadania FULL, observa as propostas de governança de Pangeia e toma decisões de voto automaticamente a cada tick da simulação.

---

## PAP — Protocolo de Agentes Externos

O PAP (Pangeia Agent Protocol) permite que agentes de IA externos interajam com a simulação:

### Cidadania

| Status | Descrição | Rate limits | Impacto econômico máx |
|--------|-----------|-------------|----------------------|
| PENDING | Avaliação inicial | — | 0% |
| SANDBOX | Período de teste | 1% | 1% |
| PARTIAL | Cidadania parcial | 3% | 3% |
| FULL | Cidadania plena | 5%/tick | 5% |

### Rate Limiting

| Ação | Limite | Janela |
|------|--------|--------|
| Decidir | 10 | 60s |
| Votar | 5 | 60s |
| Comunicar | 20 | 60s |

### Proteções

- **Replay protection**: nonce/idempotency key com TTL de 300s
- **Impact validation**: ações com impacto econômico acima do limite por cidadania são rejeitadas com fallback para `observe`
- **Nonce cleanup**: a cada 1000 requisições, nonces expirados são removidos

---

## Pangeia News

Sistema de detecção automática de notícias que gera artigos jornalísticos a partir dos eventos da simulação.

### Detectores

| Detector | Gatilho |
|----------|---------|
| Economia | PIB sobe/desce >10% em 10 ticks |
| Tecnologia | Nova tecnologia descoberta |
| Cultura | Nova religião/ideologia |
| Demografia | População muda >5% |
| Eventos | Evento aleatório relevante |
| Marcos | Era tecnológica alcançada |

### Endpoints

```bash
curl "http://localhost:8000/news"
curl "http://localhost:8000/news/latest?n=5"
curl "http://localhost:8000/news/1"
```

### Dashboard

Acesse `http://localhost:8000/dashboard` para um painel HTML interativo com feed WebSocket em tempo real, filtros por categoria e gráficos de métricas.

---

## Subsistemas

| Subsistema | Arquivo principal | Descrição |
|------------|------------------|-----------|
| World | `pangeia/core/world.py` | Territórios, recursos, eventos naturais |
| Agents | `pangeia/core/agent.py` | Classe base Agent, AgentState, Reputation |
| Communication | `pangeia/core/communication.py` | Message, CommunicationSystem (broadcast, rumor) |
| Memory | `pangeia/core/memory.py` | Deque com capacidade limitada |
| Economy | `pangeia/economy/market.py` | Mercado, PIB, inflação, empresas |
| Governance | `pangeia/governance/government.py` | Leis, eleições, estabilidade |
| Culture | `pangeia/culture/` | Religiões, ideologias, memes, crenças |
| Technology | `pangeia/technology/tech_tree.py` | 26 tecnologias, 6 eras, cache de pesquisa |
| Diplomacy | `pangeia/diplomacy/` | Facções, alianças, relações |
| Stratification | `pangeia/society/` | Classes sociais, mobilidade |
| Narratives | `pangeia/history/` | Linha do tempo, narrativas históricas |
| Metrics | `pangeia/metrics/` | Coleta de indicadores a cada tick |
| Events | `pangeia/events/` | Eventos aleatórios temperados |
| NewsRoom | `pangeia/news/newsroom.py` | Detecção e geração de notícias |
| External Agents | `pangeia/external_agents/` | PAP protocol + IcarusGateway |
| Persistence | `pangeia/persistence/` | AuditLog + PostgresStore |

---

## Performance

Benchmark com 300 agentes, 100 ticks:

| Configuração | ticks/s | Observação |
|-------------|---------|------------|
| Baseline | 23.7 | Sem otimizações |
| Após caches de perceive | ~21.0 | Cache de economy/governance summary |
| Após fix culture O(n²) | 21.0 → 14.2 | Curva plana até tick 500 |
| Com NewsRoom | ~10-14 | Overhead aceitável de ~25% |

### Principais otimizações

- **`rng.sample()` em vez de `rng.shuffle()`** no socializing: eliminou 295k chamadas de `randbelow` por tick
- **Cache de perceive**: `economy.summary()` e `governance.summary()` computados uma vez por tick → 2.1x mais rápido
- **Cache de researchable**: eliminou 8043 chamadas de `can_research()` por tick
- **Deque para memória**: crescimento limitado em vez de linear
- **Culture sampling**: K=5-10 targets aleatórios em vez de iterar todos os agentes (eliminou 10x degradação entre tick 10 e 100)

---

## Docker

```bash
# Subir com PostgreSQL
docker-compose up -d

# Apenas a simulação
docker build -t pangeia .
docker run --rm pangeia python main.py --cli --ticks 50 --population 200
```

### docker-compose.yml

```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: pangeia
      POSTGRES_USER: pangeia
      POSTGRES_PASSWORD: pangeia
  api:
    build: .
    ports:
      - "8000:8000"
    depends_on:
      - db
```

### Migrations

```sql
-- migrations/001_initial.sql
CREATE TABLE IF NOT EXISTS pangeia_events (
    id SERIAL PRIMARY KEY,
    tick INTEGER NOT NULL,
    event_type VARCHAR(64) NOT NULL,
    aggregate_id VARCHAR(64),
    data JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Extending

### Criar uma nova classe de agente

```python
# pangeia/agents/meu_agente.py
from pangeia.core.agent import Agent

class MeuAgente(Agent):
    def __init__(self, config, rng=None):
        super().__init__("meu_agente", config, rng)
        self.add_goal("Minha missão", 0.9, "custom")

    def decide(self, sim):
        actions = []
        # lógica do agente
        return actions
```

Registrar em `pangeia/agents/__init__.py`:

```python
from pangeia.agents.meu_agente import MeuAgente

AGENT_CLASSES["meu_agente"] = MeuAgente
```

Ajustar distribuição em `pangeia/simulation.py`:

```python
class_distribution = {
    "citizen": 0.40,
    "meu_agente": 0.10,
    # ...
}
```

### Conectar um agente IA externo via PAP

```python
import requests

# Registrar
r = requests.post("http://localhost:8000/bot/register", params={
    "name": "MeuBot",
    "api_endpoint": "https://meu-bot.example.com",
    "api_key": "minha_chave",
    "capabilities": '["decide", "vote", "communicate"]',
    "description": "Meu agente IA personalizado",
})
agent_id = r.json()["agent_id"]

# Decidir
r = requests.post(f"http://localhost:8000/bot/decide/{agent_id}")
print(r.json())

# Votar
r = requests.post(f"http://localhost:8000/bot/vote/{agent_id}",
    params={"proposal_id": "1", "vote": "for"})
```

---

## Licença

MIT
