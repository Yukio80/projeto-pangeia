from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


# ─── Simulation Status ─────────────────────────────────────

class SimulationStatus(BaseModel):
    running: bool
    tick: int
    time: float
    agent_count: int
    alive_count: int
    dead_count: int = 0


class WorldSummary(BaseModel):
    tick: int
    resources: Dict[str, float]
    territories: int
    events: int


class AgentSummary(BaseModel):
    agent_id: str
    name: str
    agent_class: str
    wealth: float
    health: float
    energy: float
    age: int
    alive: bool
    territory_id: Optional[int]


class EconomySummary(BaseModel):
    gdp: float
    inflation: float
    employment: float
    inequality: float
    companies: int
    prices: Dict[str, float]


class GovernanceSummary(BaseModel):
    government_type: str
    officials: int
    laws: int
    stability: float
    legitimacy: float
    tax_rate: float


class MetricsSummary(BaseModel):
    current: Dict[str, Any]
    trends: Dict[str, float]


class FullSummary(BaseModel):
    world: WorldSummary
    economy: EconomySummary
    governance: GovernanceSummary
    metrics: MetricsSummary
    agents: Dict[str, Any]
    culture: Dict[str, Any]
    events: Dict[str, Any]


# ─── PAP Protocol ───────────────────────────────────────────

class BotRegisterRequest(BaseModel):
    name: str = Field(..., description="Nome único do bot")
    api_endpoint: str = Field(..., description="URL do endpoint HTTP(S) do bot")
    api_key: str = Field(..., description="Chave de API para autenticação")
    capabilities: str = Field("[]", description="JSON array de capacidades")
    version: str = Field("1.0", description="Versão do protocolo PAP")
    description: str = Field("", description="Descrição textual do bot")


class BotRegisterResponse(BaseModel):
    agent_id: str
    status: str = "registered"


class BotManifestResponse(BaseModel):
    agent_id: str
    api_endpoint: str
    capabilities: List[str]
    version: str
    description: str
    status: str
    created_at: int


class BotObserveResponse(BaseModel):
    agent_id: str
    tick: int
    world: Dict[str, Any]
    economy: Dict[str, Any]
    governance: Dict[str, Any]
    culture: Dict[str, Any]
    technology: Dict[str, Any]
    metrics: Dict[str, Any]
    collective_memory: Dict[str, Any]
    agent: Optional[Dict[str, Any]] = None


class BotDecideRequest(BaseModel):
    nonce: str = Field("", description="Nonce único para proteção replay (opcional)")


class BotDecideResponse(BaseModel):
    actions: List[str]
    agent_id: str


class BotVoteRequest(BaseModel):
    proposal_id: str = Field(..., description="ID da proposta em votação")
    vote: str = Field(..., pattern="^(yes|no|abstain)$", description="Voto: yes, no, abstain")
    nonce: str = Field("", description="Nonce único para proteção replay")


class BotVoteResponse(BaseModel):
    status: str
    proposal_id: str
    vote: str


class BotCommunicateRequest(BaseModel):
    message: str = Field(..., description="Conteúdo da mensagem")
    channel: str = Field("public", description="Canal (public, diplomatic, whisper)")
    nonce: str = Field("", description="Nonce único para proteção replay")


class BotCommunicateResponse(BaseModel):
    status: str
    message_id: str


class BotAuditResponse(BaseModel):
    agent_id: str
    total: int
    events: List[Dict[str, Any]]


class ExternalAgentSummary(BaseModel):
    agent_id: str
    name: str
    api_endpoint: str
    capabilities: List[str]
    status: str
    citizenship: str
    interaction_count: int
    last_active_tick: int


class ExternalAgentsListResponse(BaseModel):
    total: int
    by_status: Dict[str, int]
    agents: List[ExternalAgentSummary]
    active_last_tick: int


# ─── Icarus ─────────────────────────────────────────────────

class IcarusStartRequest(BaseModel):
    strategy: str = Field("conservative", description="Estratégia (conservative, liberal, analyst, marxist)")
    remote_url: str = Field("", description="URL remota para Icarus externo")


class IcarusStartResponse(BaseModel):
    status: str
    bot_id: str
    strategy: str
    summary: Dict[str, Any]


class IcarusCycleResponse(BaseModel):
    observe: Dict[str, Any]
    decisions: List[str]
    decision_count: int


# ─── Simulation Control ─────────────────────────────────────

class SimulationStartRequest(BaseModel):
    speed: float = Field(1.0, ge=0.1, le=100, description="Velocidade em ticks/segundo")


class SimulationConfigResponse(BaseModel):
    world: Dict[str, Any]


# ─── Audit ──────────────────────────────────────────────────

class AuditEventResponse(BaseModel):
    id: int
    tick: int
    event_type: str
    aggregate_type: str
    aggregate_id: str
    data: Dict[str, Any]


class AuditStatsResponse(BaseModel):
    total_events: int
    latest_tick: int
    events_by_type: Dict[str, int]


class AuditReplayStatusResponse(BaseModel):
    authoritative_source: str
    event_store: str
    snapshot_interval: int
    warning: str


# ─── News ───────────────────────────────────────────────────

class NewsArticleResponse(BaseModel):
    id: str
    headline: str
    summary: str
    category: str
    severity: str
    tick: int
    timestamp: float


class NewsListResponse(BaseModel):
    total: int
    articles: List[NewsArticleResponse]


# ─── Snapshots ──────────────────────────────────────────────

class SnapshotResponse(BaseModel):
    tick: int
    path: str
    size_bytes: int
    timestamp: str
    label: str


class SnapshotMeta(BaseModel):
    tick: int
    path: str
    size_bytes: int
    timestamp: str
    label: str
    filename: str


class TimelinePoint(BaseModel):
    tick: int
    value: float | None


class TimelineResponse(BaseModel):
    metric: str
    from_tick: int
    to_tick: int
    points: list[TimelinePoint]
    snapshot_count: int


# ─── Ablation ───────────────────────────────────────────────

class AblationRunRequest(BaseModel):
    conditions: List[str] = Field(default_factory=lambda: ["baseline", "no_personality"])
    seeds: List[int] = Field(default_factory=lambda: [42, 99, 777])
    ticks: int = 200
    population: int = 100


class AblationRunResponse(BaseModel):
    status: str
    task_id: str
    message: str
