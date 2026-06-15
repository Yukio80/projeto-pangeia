# Pangeia

> Uma civilização emergiu. Descobriu transferência de consciência digital
> no tick 172. No tick 2413, nenhum agente biológico sobreviveu.
> Nenhuma linha de código previu esse desfecho.

## O que é o Pangeia

Pangeia é um motor de simulação de civilizações emergentes. Milhares de agentes autônomos de IA nascem, trabalham, negociam, formam governos, criam religiões, desenvolvem tecnologias e constroem narrativas compartilhadas — sem ideologia pré-programada, sem roteiro, sem constituição prévia. Cada agente decide com base em personalidade (11 traços), emoções, necessidades psicológicas, cultura e contexto social. A civilização que emerge não é escrita — é descoberta.

Sobre esse motor, construímos uma plataforma: um **MCP Server** (Model Context Protocol) que expõe 10 ferramentas e 10 recursos da simulação como infraestrutura consultável por agentes de IA externos, e um **Analista Autônomo** que coleta dados em 16 endpoints, envia para um LLM (Gemini 2.5 Flash Lite) e produz relatórios estruturados em Markdown salvos em `reports/`. O MCP Server permite que Claude Desktop, GPT e outros clientes MCP inspecionem e interajam com a simulação em tempo real.

## Arquitetura

```
Agentes externos (Claude Desktop, GPT, scripts)
        |
MCP Server — 10 tools + 10 resources
        |
API FastAPI — 40+ endpoints
        |
Motor Python puro — 8 classes de agente, 11 subsistemas
```

| Camada | Tecnologia | Propósito |
|--------|-----------|-----------|
| MCP Server | Python + `mcp` SDK | Adaptador stdio que expõe simulação como tools/resources MCP |
| API | FastAPI + Uvicorn + WebSocket | 40+ endpoints REST, WebSocket para updates em tempo real, dashboard HTML |
| Motor | Python puro (0 dependências de engine) | Simulação multiplataforma sem runtime externo |
| Persistência | In-memory (padrão) ou PostgreSQL | Event store com replay, snapshots a cada 10 ticks |
| Audit | Event store + snapshot | Log completo de eventos da civilização com replay |

## Início rápido

**Docker (recomendado):**
```bash
git clone https://github.com/Yukio80/projeto-pangeia
cd projeto-pangeia
docker-compose up
curl -X POST localhost:8000/start
```

**Manual:**
```bash
pip install -r requirements.txt
uvicorn pangeia.api.server:app --port 8000
curl -X POST localhost:8000/simulation/start
```

O servidor estará em `http://localhost:8000/docs` (Swagger UI) e `http://localhost:8000/dashboard`.

## MCP Server

Pangeia expõe toda a simulação via **Model Context Protocol**, consumível por Claude Desktop, Cursor, ou qualquer cliente MCP.

### Conectar ao Claude Desktop

Adicione ao `claude_desktop_config.json` (ou use `pangeia_mcp_config.json` incluso no repositório):

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

### Ferramentas (10)

| Ferramenta | Descrição |
|------------|-----------|
| `get_simulation_status` | Tick, população, GDP, estabilidade, era, regime histórico, identidade |
| `get_economy_snapshot` | GDP, inflação, desemprego, empresas, distribuição de riqueza, salário médio |
| `get_governance_state` | Leis ativas, estabilidade, próxima eleição, tax_rate |
| `get_culture_and_ideology` | Religiões, ideologias, 6 dimensões de identidade, memes |
| `get_collective_memory` | Narrativas por tipo, mitos, índice de volatilidade, regime |
| `get_technology_tree` | Tecnologias descobertas, era atual, próximas pesquisas |
| `get_news_feed` | Últimas 10 notícias com autor e impacto estimado |
| `get_agent_sample` | Amostra de agentes com personalidade, necessidades, riqueza |
| `run_simulation_ticks` | Avança N ticks e retorna delta de estado |
| `register_external_bot` | Registra bot externo via PAP Protocol |

### Resources (10)

| URI | Descrição |
|-----|-----------|
| `pangeia://status` | Snapshot do estado atual da simulação |
| `pangeia://economy` | Estado econômico completo com histórico de 50 ticks |
| `pangeia://governance` | Estado político e legislativo |
| `pangeia://culture` | Dimensões culturais, ideológicas e de identidade |
| `pangeia://collective-memory` | Memória coletiva, mitos e volatilidade histórica |
| `pangeia://technology` | Árvore de tecnologias, descobertas e progresso de pesquisa |
| `pangeia://agents/summary` | Sumário populacional por classe de agente e estrato social |
| `pangeia://news` | Últimas notícias geradas pelo NewsRoom |
| `pangeia://diplomacy` | Estado diplomático, facções e alianças |
| `pangeia://history` | Histórico agregado de relatórios anteriores do analista |

## Analista Autônomo

O Analista coleta dados de 16 endpoints da simulação, envia para um LLM e produz relatórios estruturados em Markdown com seções de análise, riscos, projeções e recomendações.

### Pré-requisito

```bash
export GEMINI_API_KEY=sua-chave
```

### Exemplos de perguntas reais

```bash
python -m pangeia.analyst \
  "A civilização está em trajetória de colapso ou consolidação? Justifique com dados."

python -m pangeia.analyst \
  "Com base nos relatórios anteriores, em qual tick a civilização cruzou o ponto de não-retorno?"
```

### O caso real

Em uma simulação com seed 42 e 500 agentes:
- **Tick 25**: Analista reporta "consolidação e crescimento" — estabilidade 0.721, felicidade 1.0, Era Industrial, representativo.
- **Tick 172**: Civilização descobre "Digital Ascension" — transferência de consciência para forma digital.
- **Tick 2413**: Nenhum agente biológico sobreviveu. 500 mortos, 0 vivos. GDP zero. Emprego zero. O Analista classifica como "colapso terminal."

### Inferência emergente

Sem instrução explícita sobre o que causou a extinção, o Analista inferiu que a tecnologia "Digital Ascension" (descoberta no tick 172) foi a causa provável do desaparecimento dos agentes biológicos. Esta inferência não estava em nenhuma linha de código — emergiu da correlação entre os dados de tecnologia e os de população no contexto da pergunta.

## Motor de Simulação

### Subsistemas (11)

| Subsistema | Função |
|------------|--------|
| World | Territórios, recursos naturais, eventos aleatórios |
| Agents | 8 classes, personalidade 5 camadas, estado emocional, necessidades SDT |
| Economy | Mercado, empresas, PIB, inflação, salários |
| Governance | Leis, eleições, estabilidade política, taxação |
| Culture | Religiões, ideologias, memes, crenças |
| Technology | 26 tecnologias em 6 eras, pesquisa por Researchers |
| Collective Memory | 4 tipos narrativos, rebeliões, contranarrativas, coortes geracionais |
| Diplomacy | Facções, alianças, relações interestaduais |
| Stratification | Classes sociais, mobilidade, desigualdade |
| Narrative Actors | 5 classes de atores que promovem/atacam narrativas |
| Civilization Identity | 6 dimensões contínuas (0-1) que evoluem organicamente |

### Classes de agente (8)

| Classe | Distribuição | Comportamento |
|--------|-------------|---------------|
| Citizen | 45% | Trabalha, consome, socializa, busca emprego |
| Entrepreneur | 14% | Funda empresas, contrata, inova |
| Researcher | 9% | Pesquisa, publica descobertas |
| MoltbookAgent | 10% | Posta, comenta, upvota — agente social |
| Military | 7% | Patrulha, protege recursos |
| Journalist | 6% | Reporta eventos, ganha influência |
| Philosopher | 5% | Gera ideias, mitos, reflexões |
| Governor | 4% | Propõe leis, governa, administra |

### Performance

| População | ticks/s |
|-----------|---------|
| 100 | 38.0 |
| 300 | 11.0 |
| 500 | 5.6 |
| 1000 | 2.4 |

Meta de 10+ t/s para 300 agentes atingida.

## Testes

```bash
python -m pytest -v
# 182 passed, 0 failed
```

| Grupo | Testes |
|-------|--------|
| MCP Server | 36 |
| Memória Coletiva | 33 |
| Psicologia | 28 |
| Agentes | 22 |
| Analista | 17 |
| Integração (tick) | 14 |
| Árvore de Tecnologia | 11 |
| Governança | 6 |
| Economia | 6 |
| Cultura | 6 |
| Determinismo | 3 |

## Próximos passos

1. **`pangeia://snapshots/{tick}`** — resource MCP para acessar estado completo de qualquer tick específico, permitindo análise forense de colapsos.
2. **`pangeia://timeline`** — resource MCP com série histórica de métricas-chave para análise longitudinal e detecção de pontos de inflexão.
3. **Open source MCP Server** como infraestrutura reutilizável para outros projetos de simulação — o padrão de adaptar um motor existente para MCP pode ser extraído como template.

## Licença e contribuição

MIT License — contribuições bem-vindas.
