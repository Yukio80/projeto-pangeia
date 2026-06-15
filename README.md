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
- [Sistema de Personalidade](#sistema-de-personalidade)
- [Memória Coletiva](#memória-coletiva)
- [NarrativeActor](#narrativeactor)
- [CivilizationIdentity](#civilizationidentity)
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

### Memória Coletiva

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/collective_memory` | Sumário completo (narrativas, rebeliões, identidade, atores, volatilidade) |
| `GET` | `/collective_memory/myths` | Mitos ativos (narrativas com 3+ gerações) |
| `GET` | `/collective_memory/volatility` | Métrica composta de volatilidade histórica |
| `GET` | `/collective_memory/narratives/{type}` | Narrativas por tipo (foundational/reformist/revolutionary/myth) |
| `GET` | `/collective_memory/identity` | Identidade da civilização (6 dimensões) |
| `GET` | `/collective_memory/actors` | Atores narrativos (quem promove/ataca cada narrativa) |
| `GET` | `/collective_memory/actors/{agent_id}` | Detalhes de um ator específico |

### Agentes externos (PAP)

| Método | Rota | Descrição |
|--------|------|-----------|

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
                    │  (35+ endpoints + WebSocket) │
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
     │Companies│  │  ~8 classes de agentes    │   │  (PAP)      │
     └────────┘   │  Personalidade 5 camadas  │   └──────┬──────┘
                  │  Memória coletiva          │          │
                  └──────────┬────────────────┘          │
                             │                           │
                ┌────────────┼───────────────────────────┘
                │            │
           ┌────▼────┐  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐
           │World    │  │Culture  │  │Governance│  │Tech     │
           │Recursos │  │Religião │  │Leis      │  │Árvore   │
           │Eventos  │  │Ideologia│  │Eleições  │  │26 techs │
           │Territó. │  │Memes    │  │Votações  │  │6 eras   │
           └─────────┘  └─────────┘  └─────────┘  └─────────┘
           ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐
           │Narrative│  │Collect. │  │Civiliz. │  │Icarus   │
           │Actors   │  │Memory   │  │Identity │  │Gateway  │
           │(5 roles)│  │4 tipos  │  │6 dims   │  │4 strat. │
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
9. **Personalidade** — evolução lenta (mutate 0.005), necessidades, memória emocional
10. **CollectiveMemory.step()** — gerações, rebeliões, contranarrativas
11. **NarrativeActor.step()** — atores promovem/atacam narrativas
12. **CivilizationIdentity** — identidade é recomputada
13. **Metrics** — coleta de indicadores
14. **NewsRoom** — detecção de eventos noticiáveis
15. **Icarus** — ciclo de observação e decisão
16. **AuditLog** — persistência

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

- **Personalidade**: 11 traços de Temperamento (distribuição normal), 9 Arquétipos, 30+ perfis emocionais
- **Estado emocional** com decay e memória emocional
- **Necessidades psicológicas**: autonomia, competência, pertencimento (Self-Determination Theory)
- **AgentBehaviorModifiers** + **CulturalInfluence**
- **Metas** autônomas com prioridades
- **Memória** curta (deque 10) e longa (deque 50)
- **Conhecimento** (crenças verdadeiras/falsas)
- **Rede social** (relacionamentos com confiança/influência)
- **Reputação** por agente
- **Habilidades** aprendidas (limitadas a 10)
- **Eventos de vida** (últimos 50)

### Fórmula de Decisão

```
Decision = Temperament(0.25) + Emotions(0.20) + Needs(0.15)
         + Experiences(0.15) + Culture(0.15) + Context(0.10)
```

Cada agente tem um `AgentArchetype` que define trait_modifiers, preferred_actions e preferred_goals. A personalidade evolui lentamente (mutate rate = 0.005/tick). Contradições internas podem surgir (6 pares, 15% de chance na criação).

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

## Sistema de Personalidade

A personalidade de cada agente é um sistema de 5 camadas que interagem para produzir decisões:

### 1. Temperamento (11 traços)

Cada traço tem distribuição normal independente (média 0, desvio 1):

| Traço | Descrição |
|-------|-----------|
| Extraversion | Energia social, busca de estímulos |
| Agreeableness | Cooperação, confiança nos outros |
| Conscientiousness | Autodisciplina, organização |
| Neuroticism | Instabilidade emocional, ansiedade |
| Openness | Curiosidade intelectual, criatividade |
| Honesty-Humility | Sinceridade, modéstia, justiça |
| Assertiveness | Dominância social, liderança |
| Compassion | Empatia, preocupação com o próximo |
| Orderliness | Apego a regras, rotina, estrutura |
| Volatility | Reatividade emocional, intensidade |
| Withdrawal | Tendência a evitar conflito ou risco |

Evolução: `mutate(rate=0.005)` por tick — mudanças lentas e realistas.

### 2. Arquétipos (9 tipos)

| Arquétipo | Traços elevados | Ações preferidas |
|-----------|-----------------|------------------|
| Sage | Openness, Conscientiousness | research, teaching |
| Ruler | Assertiveness, Conscientiousness | govern, make_speech |
| Warrior | Assertiveness, Volatility | patrol, military_action |
| Caregiver | Compassion, Agreeableness | socializing, teaching |
| Explorer | Openness, Extraversion | explore, research |
| Creator | Openness, Conscientiousness | innovate, research |
| Rebel | Volatility, Withdrawal (-) | protest, disrupt |
| Lover | Extraversion, Compassion | socializing, relationship |
| Jester | Extraversion, Openness | entertain, socialize |

### 3. Memória Emocional

Cada evento significativo gera um perfil emocional com 30+ tipos (war, discovery, betrayal, cultural_renaissance, etc.). Decay natural de 0.002/tick. As emoções de eventos recentes influenciam diretamente as decisões do agente.

### 4. Necessidades Psicológicas (SDT)

Três necessidades básicas que decaem com o tempo e são satisfeitas por ações:
- **Autonomia**: satisfeita por liberdade de escolha, riqueza
- **Competência**: satisfeita por trabalho, pesquisa, descobertas
- **Pertencimento**: satisfeita por relacionamentos, socialização

### 5. Influência Cultural

A cultura dominante (religião, ideologia) molda as preferências do agente com peso 0.15 na decisão final.

### Contradições

Agentes podem ter contradições internas (ex: alta Honesty + alta Volatility = "impulso sincero"). 6 pares de traços antagônicos com 15% de chance de ativação na criação.

---

## Memória Coletiva

A memória coletiva da civilização armazena narrativas compartilhadas que moldam a identidade cultural. Narrativas não são factuais — são **interpretações** do que aconteceu.

### Tipos de Narrativa

| Tipo | Origem | Função |
|------|--------|--------|
| **Foundational** | Eventos fundacionais, descobertas, religião | Base da tradição |
| **Reformist** | Contranarrativa gerada em rebeliões | Mudança gradual |
| **Revolutionary** | Contranarrativa radical (50% das rebeliões) | Ruptura completa |
| **Myth** | Foundational após 3+ gerações com alta importância | Lenda, identidade sagrada |

### Ciclo de Vida

1. Evento significativo → memória coletiva (dominância inicial 0.3-0.7)
2. Cada geração (20 ticks): memórias envelhecem, importância decai
3. Se dominância média > 0.6: probabilidade de rebelião acumula
4. Rebelião: narrativas dominantes são desafiadas, contranarrativas surgem
5. Contranarrativas viram novas tradições → ciclo recomeça

### Coortes Geracionais

| Faixa | Idade | Viés de rebeldia |
|-------|-------|-----------------|
| Young | ≤30 ticks | 1.4× |
| Adult | 31-100 | 0.8× |
| Elder | 100+ | 0.3× |

Jovens empurram mudança, velhos preservam. O viés é aplicado ao drift político de cada agente.

### HistoricalVolatility

Métrica composta de 5 componentes:

| Componente | Peso | Descrição |
|-----------|------|-----------|
| rebellion_count | 0.25 | Frequência de rebeliões |
| narrative_turnover | 0.25 | Proporção de reformist+revolutionary |
| emotional_polarization | 0.20 | Variância emocional entre memórias |
| myth_formation_rate | 0.15 | Taxa de formação de mitos |
| dominance_oscillation | 0.15 | Oscilação da dominância recente |

**Regimes**: estável (<0.15) → instável → revolucionária → decadente → fragmentada (≥0.60)

---

## NarrativeActor

Narrativas não se espalham porque existem — espalham-se porque alguém as promove. Um ator com alta influência e carisma pode tornar dominante uma narrativa mediana; um ator isolado pode ter a melhor ideia da história e ninguém ouvir.

### Classes de atores

| Classe | Influência | Ideologia | Narrativa preferida |
|--------|-----------|-----------|-------------------|
| Governor | 0.7 | conservative | foundational (preserva instituições) |
| Journalist | 0.5 | neutral | reformist (busca verdade) |
| Philosopher | 0.6 | progressive | reformist (questiona) |
| Researcher | 0.4 | progressive | reformist (inova) |
| Military | 0.5 | conservative | foundational (defende ordem) |

### Comportamento

A cada tick, cada ator tem 15% de chance de agir:
- **60% promover**: aumenta dominância + importância de narrativa alinhada à sua ideologia
- **40% atacar**: reduz dominância + importância de narrativa contrária à sua ideologia

Poder efetivo: `influence × charisma × (1 + log10(audience))`

Um governador conservador promove narrativas foundational e ataca revolutionary. Um filósofo progressista promove reformist e ataca foundational.

---

## CivilizationIdentity

A identidade cultural emerge automaticamente do estado atual do sistema — não é um label fixo, mas 6 dimensões contínuas (0-1) que podem ser observadas evoluindo ao longo dos ticks.

### Dimensões

| Dimensão | Fonte |
|----------|-------|
| **religiosity** | Memórias religiosas + espiritualidade emocional |
| **militarism** | Eventos de guerra/conflito + agressividade |
| **individualism** | Polarização emocional (alta = mais individualista) |
| **traditionalism** | Proporção de narrativas foundational + myth |
| **innovation** | Tecnologias descobertas + curiosidade coletiva |
| **pluralism** | Diversidade de tipos narrativos ativos |

### Divergência entre civilizações

`CivilizationIdentity.divergence_report()` compara múltiplas identidades e mede divergência (std) em cada dimensão. Experimento com 5 seeds diferentes (42, 99, 123, 456, 777) após 500 ticks:

```
Avg divergence across all dims: 0.093
Maior divergente: pluralism (std=0.245, range [0.5, 1.0])
2 tendências emergindo: tradicionalista vs individualista
```

Com seeds suficientes, civilizações começam a trilhar trajetórias históricas divergentes a partir das mesmas regras fundamentais — validação forte do modelo.

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
| Agents | `pangeia/core/agent.py` | Classe base Agent, AgentState, Reputation, Personalidade 5 camadas |
| Psychology | `pangeia/core/psychology.py` | Temperamento (11 traços), 9 Arquétipos, Necessidades SDT, Memória Emocional |
| Communication | `pangeia/core/communication.py` | Message, CommunicationSystem (broadcast, rumor) |
| Memory | `pangeia/core/memory.py` | Deque com capacidade limitada |
| CollectiveMemory | `pangeia/core/collective_memory.py` | 4 tipos narrativos, rebeliões, gerações, NarrativeActor, CivilizationIdentity, HistoricalVolatility |
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

Benchmarks atuais (versão otimizada com 1000 agentes):

| População | ticks/s | Observação |
|-----------|---------|------------|
| 100 | 38.0 | Otimizado |
| 300 | 11.0 | Acima da meta (>10 t/s) |
| 500 | 5.6 | — |
| 1000 | 2.4 | Gargalo: objeto Agent (overhead Python) |

### Principais Otimizações Recentes (2026)

- **`_process_action` dict dispatch (42x mais rápido)**: Substituiu `if/elif` por dispatch O(1).
- **Moltbook O(k) sampling**: Amostragem K=10/20 em vez de iterar sobre toda a população (O(n²)).
- **Redução de syscalls**: Removido `time.time()` de `memory.remember()` e `broadcast` targets reduzido (50 -> 20/30).
- **Personality/Evolution**: Evolução (mutate/decay) a cada 2 ticks; trim de memória emocional a cada 5 ticks.
- **Cache de percepção**: Caches de `economy.summary()` e `governance.summary()` reduziram drasticamente recomputação O(n²).

### Resultados experimentais

**Batalha cultural** (500 ticks, 30 agentes):
- 875 memórias coletivas (334 foundational, 333 reformist, 168 revolutionary, 40 myths)
- 1 rebelião, regime instável
- 9 atores narrativos ativos (mais poderoso: governor com power=1.063)
- Tendência dominante: individualista

**Divergência entre civilizações** (5 seeds, 500 ticks):

| Dimensão | Média | Desvio | Range |
|----------|-------|--------|-------|
| pluralism | 0.80 | 0.245 | [0.5, 1.0] |
| traditionalism | 0.86 | 0.130 | [0.684, 1.0] |
| religiosity | 0.188 | 0.082 | [0.081, 0.267] |
| innovation | 0.405 | 0.064 | [0.312, 0.469] |
| individualism | 0.98 | 0.024 | [0.95, 1.0] |
| militarism | 0.694 | 0.013 | [0.677, 0.714] |

2 tendências emergindo: **tradicionalista** (seeds 42, 99) vs **individualista** (seeds 123, 456, 777).

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

## MCP Server

Pangeia expõe o motor da simulação como **ferramentas MCP** (Model Context Protocol),
consumíveis por agentes de IA como Claude Desktop, GPT, ou qualquer cliente MCP.

### Arquitetura

```
┌──────────────────────┐       stdio        ┌──────────────────────┐
│   Claude Desktop /   │ ◄───────/───────── │   pangeia/mcp_server.py  │
│   Cliente MCP        │                    │   (MCP → HTTP proxy)  │
│                      │                    │            │          │
│                      │                    │     HTTP interno      │
│                      │                    │            │          │
│                      │                    │  ┌─────────▼────────┐ │
│                      │                    │  │  FastAPI Server   │ │
│                      │                    │  │  localhost:8000   │ │
│                      │                    │  └──────────────────┘ │
└──────────────────────┘                    └──────────────────────┘
```

### Ferramentas disponíveis

| Ferramenta | Descrição |
|------------|-----------|
| `get_simulation_status` | Tick, população, GDP, estabilidade, era, regime histórico, identidade |
| `get_economy_snapshot` | GDP, inflação, desemprego, empresas, distribuição, salário médio |
| `get_governance_state` | Leis, estabilidade, eleições, tax_rate |
| `get_culture_and_ideology` | Religiões, ideologias, 6 dimensões de identidade, memes |
| `get_collective_memory` | Narrativas por tipo, mitos, volatilidade, regime |
| `get_technology_tree` | Tecnologias descobertas, era, próximas pesquisas |
| `get_news_feed` | Últimas 10 notícias |
| `get_agent_sample` | Amostra de agentes com personalidade, necessidades, riqueza |
| `run_simulation_ticks` | Avança N ticks e retorna delta de estado |
| `register_external_bot` | Registra bot externo via PAP Protocol |

### Configuração para Claude Desktop

Adicione ao seu `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "pangeia": {
      "command": "python",
      "args": ["pangeia/mcp_server.py"],
      "env": {
        "PANGEIA_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

Ou use o arquivo `pangeia_mcp_config.json` já incluído no projeto.

### Uso direto

```bash
# O servidor MCP usa protocolo stdio (padrão MCP)
python pangeia/mcp_server.py

# Configure a URL da API (opcional, padrão http://localhost:8000)
PANGEIA_API_URL=http://localhost:8000 python pangeia/mcp_server.py
```

### Importante

- O MCP Server **não modifica** o motor da simulação — é apenas um adaptador HTTP → MCP.
- A API FastAPI (`python main.py`) **deve estar rodando** para o MCP funcionar.
- Se a simulação estiver parada, use `run_simulation_ticks` para iniciá-la.
- Timeout por chamada: 30 segundos.

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
