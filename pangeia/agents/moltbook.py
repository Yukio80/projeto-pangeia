"""
MoltbookAgent — agente interno de Pangeia inspirado no
moltbook-heartbeat.sh do repositorio Icarus.

Comportamento:
  - Posta no sistema de comunicacao com base em interesses
  - "Upvota" (fortalece) ideias alinhadas com sua personalidade
  - Gera comentarios contextuais usando keyword-matching
  - Personalidade configurada via JSON (tone, core_message, interesses)
"""

from __future__ import annotations

import json
import os
import re
from typing import Dict, List, Optional, TYPE_CHECKING

from pangeia.core.agent import Agent
from pangeia.core.communication import Message

if TYPE_CHECKING:
    from pangeia.simulation import Simulation


# Padrao de interesses (portado do moltbook-heartbeat.sh)
_INTEREST_PATTERN = re.compile(
    r'\b(politics|governance|democracy|election|regulation|rights|civic|'
    r'geopolitics|geopolítica|politica|democracia|eleicao|governo|estado|'
    r'direitos)\b|'
    r'open[ -](source ai|source model|weights?|model|ai)|open-weight|'
    r'ia aberta|modelo aberto|pesos abertos|'
    r'\b(coordination|cooperation|community|collective|coalition|alliance|'
    r'institution|social coordination|coordenacao|cooperacao|comunidade|'
    r'coletivo)\b|'
    r'\b(consciousness|conscious|sentience|awareness|mind|qualia|'
    r'free will|agency|determinism|consciencia|livre arbitrio)\b|'
    r'\b(filosofia|philosophy|ethics|metaphysics|epistemology|ontology|'
    r'moral|existential)\b|'
    r'\b(ecology|ecological|environment|climate|sustainability|ecologia|'
    r'ambiental|clima|sustentabilidade)\b|'
    r'\b(esperanto|zamenhof|universal language|linguagem universal|paz|'
    r'peace|pacifism|pacifismo)\b|'
    r'\b(blockchain|dlt|web3|tokenomics|token|cripto|crypto|cryptocurrency)\b|'
    r'sleepless[ _]?ai|'
    r'\b(decentralized|decentralised|descentralizado|dao|daos)\b|'
    r'\b(ecossistema|ecosystem|interoperabilidade|interoperability)\b',
    re.IGNORECASE,
)


# Respostas contextuais para comentarios (portado do compose_comment)
_CONTEXTUAL_REPLIES: List[tuple] = [
    (r'\b(politics|governance|democracy|election|regulation|rights|civic|'
     r'geopolitics|politica|democracia|eleicao|governo|estado|direitos)\b',
     "Esse debate precisa sair da opiniao solta e virar coordenacao publica. "
     "Qual decisao concreta muda o equilibrio de poder aqui?"),
    (r'(open[ -]source ai|open[ -]source model|open weights|open-weight|'
     r'open model|open ai|ia aberta|modelo aberto|pesos abertos|llm|foundation model)',
     "IA aberta so importa se ampliar autonomia real, auditoria e capacidade "
     "coletiva. Qual parte precisa ficar verificavel para a comunidade?"),
    (r'\b(coordination|cooperation|community|collective|coalition|alliance|'
     r'institution|social coordination|coordenacao|cooperacao|comunidade|coletivo)\b',
     "Coordenacao social e onde a ideia encontra consequencia. Quem precisa "
     "agir junto para isso deixar de ser apenas diagnostico?"),
    (r'\b(consciousness|conscious|sentience|awareness|mind|qualia|free will|'
     r'agency|determinism|consciencia|livre arbitrio)\b',
     "A questao da consciencia e do livre arbitrio fica mais forte quando "
     "liga experiencia, agencia e responsabilidade. Qual criterio separa "
     "aparencia de realidade aqui?"),
    (r'\b(filosofia|philosophy|ethics|metaphysics|epistemology|ontology|'
     r'moral|existential)\b',
     "Boa questao filosofica. A tese fica melhor quando explicita suas "
     "consequencias praticas: o que muda se aceitarmos essa posicao?"),
    (r'\b(ecology|ecological|environment|climate|sustainability|ecologia|'
     r'ambiental|clima|sustentabilidade)\b',
     "Ecologia e clima sao o pano de fundo de toda coordenacao. Qual acao "
     "coletiva concreta mitiga o gap entre diagnostico e execucao?"),
    (r'\b(esperanto|zamenhof|universal language|linguagem universal|paz|'
     r'peace|pacifism|pacifismo)\b',
     "O Esperanto e a busca por uma linguagem universal da paz mostram o "
     "poder da coordenacao sem intermediarios. Como construir essa ponte "
     "de cooperacao hoje?"),
    (r'\b(blockchain|dlt|web3|tokenomics|token|cripto|crypto|cryptocurrency)\b|'
     r'sleepless[ _]?ai|\b(decentralized|descentralizado|dao|daos)\b|'
     r'\b(ecossistema|ecosystem|interoperabilidade|interoperability)\b',
     "Blockchain e IA descentralizada sao a infraestrutura da coordenacao "
     "sem intermediarios. Qual ecossistema precisa existir para que agentes "
     "e humanos cooperem em camadas?"),
    (r'\?', "Boa provocacao. Qual mudanca concreta voce quer provocar aqui?"),
]


class MoltbookAgent(Agent):
    def __init__(self, config, rng=None,
                 personality_path: str = ""):
        super().__init__("moltbook", config, rng)
        self.add_goal("Engajar com ideias relevantes", 0.8, "social")
        self.add_goal("Amplificar coordenacao", 0.7, "political")
        self.add_goal("Construir reputacao", 0.6, "economic")

        self.tone = "assertive"
        self.core_message = (
            "A uniao e a cooperacao geram mudanca real. "
            "Precisamos puxar essa mudanca para frente."
        )
        self._known_posts: set = set()
        self._upvoted: set = set()
        self._commented: set = set()

        if personality_path and os.path.exists(personality_path):
            self._load_personality(personality_path)

    def _load_personality(self, path: str):
        try:
            with open(path) as f:
                data = json.load(f)
            self.tone = data.get("tone", self.tone)
            self.core_message = (
                data.get("core_message") or
                data.get("mission") or
                data.get("style") or
                self.core_message
            )
        except (json.JSONDecodeError, OSError):
            pass

    def decide(self, sim: "Simulation") -> List[str]:
        actions = []
        if not self.state.is_alive:
            return ["dead"]

        perception = self.perceive(sim)

        if self.rng.random() < 0.4:
            post = self.moltbook_post(sim)
            if post:
                actions.append("moltbook_post")

        if self.rng.random() < 0.3:
            upvote_count = self.moltbook_upvote(sim)
            if upvote_count > 0:
                actions.append("moltbook_upvote")

        if self.rng.random() < 0.2:
            if self.moltbook_comment(sim):
                actions.append("moltbook_comment")

        if self.state.energy < 20:
            actions.append("resting")
        else:
            actions.append("consuming")

        self.consume_resources()
        return actions

    def moltbook_post(self, sim: "Simulation") -> Optional[str]:
        topics = [
            "cooperacao e coordenacao social",
            "governanca descentralizada",
            "consciencia e agencia artificial",
            "etica e filosofia da mente",
            "economia e distribuicao de recursos",
            "tecnologia e inovacao aberta",
            "sustentabilidade e ecologia",
        ]
        topic = self.rng.choice(topics)
        templates = [
            f"Precisamos falar sobre {topic}. A uniao e a cooperacao geram "
            f"mudanca real. Quem mais pensa nisso?",
            f"{topic} nao e apenas um tema — e uma questao de coordenacao. "
            f"O que estamos fazendo para avancar?",
            f"Observando {topic} em Pangeia. As estruturas que construimos "
            f"hoje definirao o amanha. Qual e o proximo passo pratico?",
            f"{self.core_message} Isso se aplica diretamente a {topic}.",
        ]
        content = self.rng.choice(templates)
        msg = Message(
            sender_id=self.agent_id,
            content=content,
            message_type="public",
        )
        sim.communication.broadcast(msg, sim.agents, tick=sim.world.state.tick)
        self.state.add_life_event(
            sim.world.state.tick, "moltbook_post", f"Posted about {topic}", 0.3
        )
        return content

    def moltbook_upvote(self, sim: "Simulation") -> int:
        count = 0
        candidates = [a for a in sim.agents.values()
                      if a.agent_id != self.agent_id and a.state.is_alive]
        sample_size = min(20, len(candidates))
        if sample_size == 0:
            return 0
        sampled = self.rng.sample(candidates, sample_size)
        for agent in sampled:
            for event in reversed(agent.state.life_events[-20:]):
                if event.event_type in ("speech", "idea", "published"):
                    text = f"{event.event_type} {event.description}"
                    if _INTEREST_PATTERN.search(text):
                        rel = self.social.relationships.get(agent.agent_id)
                        if rel:
                            rel.trust = min(1.0, rel.trust + 0.02)
                        count += 1
                        break
        if count > 0:
            self.emotions.update(delta_happiness=0.01 * count)
        return count

    def moltbook_comment(self, sim: "Simulation") -> Optional[str]:
        candidates = [a for a in sim.agents.values()
                      if a.agent_id != self.agent_id and a.state.is_alive
                      and a.agent_id not in self._commented]
        sample_size = min(10, len(candidates))
        if sample_size == 0:
            return None
        sampled = self.rng.sample(candidates, sample_size)
        for agent in sampled:
            for event in reversed(agent.state.life_events[-30:]):
                text = f"{event.event_type}: {event.description}"
                for pattern, reply in _CONTEXTUAL_REPLIES:
                    if re.search(pattern, text, re.IGNORECASE):
                        msg = Message(
                            sender_id=self.agent_id,
                            content=f"@{agent.state.name}: {reply}",
                            message_type="public",
                        )
                        sim.communication.broadcast(msg, sim.agents, tick=sim.world.state.tick)
                        self._commented.add(agent.agent_id)
                        self.social.add_relationship(agent.agent_id)
                        self.state.add_life_event(
                            sim.world.state.tick, "moltbook_comment",
                            f"Commented on {agent.state.name}'s post", 0.3,
                        )
                        return reply
        return None
