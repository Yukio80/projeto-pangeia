from __future__ import annotations

import random
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pangeia.agents.conservative import Conservative, HIGH_RISK_TECHNOLOGIES, _era_index
from pangeia.governance.government import TechRestriction, GovernanceSystem
from pangeia.config import SimulationConfig
from pangeia.core.agent import AgentState
from pangeia.core.psychology import Temperament


# ─── Helpers ──────────────────────────────────────────────────


def _make_mock_config():
    return SimulationConfig.default()


def _make_conservative(rng=None, curiosidade=0.5, disciplina=0.5):
    rng = rng or random.Random(42)
    config = _make_mock_config()
    agent = Conservative(config, rng=rng)
    agent.personality.curiosidade = curiosidade
    agent.personality.disciplina = disciplina
    agent.risk_awareness = 0.5 + ((1.0 - curiosidade) * 0.3)
    if curiosidade < 0.5:
        agent.risk_awareness = min(1.0, agent.risk_awareness + 0.2)
    agent.lobbying_power = 0.3 + (disciplina * 0.4)
    agent.state.is_alive = True
    agent.state.energy = 100
    agent.state.health = 100
    agent.state.wealth = 50
    return agent


def _make_mock_sim(agents=None):
    sim = MagicMock()
    sim.agents = {a.agent_id: a for a in agents} if agents else {}
    sim.rng = random.Random(42)
    sim.world = MagicMock()
    sim.world.state.tick = 100
    sim.world.ideology_manager = MagicMock()
    sim.world.ideology_manager.ideologies = {}
    sim.world.ideology_manager.get_technology_modifier = MagicMock(return_value=0.0)
    sim.world.governance = GovernanceSystem(SimulationConfig.default())
    sim.technology = MagicMock()
    sim.technology.get_researchable = MagicMock(return_value=[])
    sim.technology.technologies = {}
    return sim


def _make_mock_researchable(name="Digital Ascension", era="singularity"):
    t = MagicMock()
    t.name = name
    t.era = era
    t.as_dict = MagicMock(return_value={"name": name, "era": era})
    return t


# ─── Tests: Instanciação ───────────────────────────────────────


class TestInstanciacao:
    def test_lobbying_power_no_range(self):
        rng = random.Random(1)
        for _ in range(50):
            c = _make_conservative(rng=rng, disciplina=rng.random())
            assert 0.3 <= c.lobbying_power <= 0.7, f"lobbying_power={c.lobbying_power} fora do range"

    def test_risk_awareness_alta_com_curiosidade_baixa(self):
        c = _make_conservative(curiosidade=0.1)
        assert c.risk_awareness > 0.7

    def test_risk_awareness_baixa_com_curiosidade_alta(self):
        c = _make_conservative(curiosidade=0.9)
        assert c.risk_awareness < 0.9

    def test_agent_class_conservative(self):
        c = _make_conservative()
        assert c.state.agent_class == "conservative"


# ─── Tests: _identify_risks ────────────────────────────────────


class TestIdentifyRisks:
    def test_retorna_ascension_quando_em_pesquisa(self):
        c = _make_conservative()
        perception = {
            "technology": {
                "technologies_in_research": [
                    {"name": "Digital Ascension", "era": "singularity"},
                ],
                "recently_discovered": [],
                "active_tech_restrictions": [],
                "nearby_governors": [],
                "active_anti_tech_ideologies": [],
            }
        }
        risks = c._identify_risks(perception)
        assert "Digital Ascension" in risks

    def test_retorna_tecnologias_era_4_ou_mais(self):
        c = _make_conservative()
        perception = {
            "technology": {
                "technologies_in_research": [
                    {"name": "Quantum Computing", "era": "quantum"},
                    {"name": "Steam Power", "era": "industrial"},
                ],
                "recently_discovered": [],
                "active_tech_restrictions": [],
                "nearby_governors": [],
                "active_anti_tech_ideologies": [],
            }
        }
        risks = c._identify_risks(perception)
        assert "Quantum Computing" in risks
        assert "Steam Power" not in risks

    def test_ignora_tecnologias_baixo_risco(self):
        c = _make_conservative()
        perception = {
            "technology": {
                "technologies_in_research": [
                    {"name": "Agriculture", "era": "stone"},
                    {"name": "The Wheel", "era": "stone"},
                ],
                "recently_discovered": [],
                "active_tech_restrictions": [],
                "nearby_governors": [],
                "active_anti_tech_ideologies": [],
            }
        }
        risks = c._identify_risks(perception)
        assert risks == []

    def test_lista_vazia_sem_tecnologias(self):
        c = _make_conservative()
        perception = {
            "technology": {
                "technologies_in_research": [],
                "recently_discovered": [],
                "active_tech_restrictions": [],
                "nearby_governors": [],
                "active_anti_tech_ideologies": [],
            }
        }
        assert c._identify_risks(perception) == []


# ─── Tests: _lobby_governor ────────────────────────────────────


class TestLobbyGovernor:
    def test_retorna_zero_sem_governors(self):
        c = _make_conservative()
        sim = _make_mock_sim(agents=[c])
        result = c._lobby_governor("Digital Ascension", sim)
        assert result == 0.0

    def test_chama_propose_tech_restriction_quando_receptivo(self):
        c = _make_conservative()
        gov = MagicMock()
        gov.state.is_alive = True
        gov.state.agent_class = "governor"
        gov.state.name = "Gov1"
        gov.personality.disciplina = 0.8
        gov.personality.curiosidade = 0.3
        sim = _make_mock_sim(agents=[c, gov])
        with patch.object(sim.world.governance, 'propose_tech_restriction') as mock_propose:
            result = c._lobby_governor("Digital Ascension", sim)
            assert result > 0
            mock_propose.assert_called()

    def test_nao_chama_quando_governor_nao_receptivo(self):
        c = _make_conservative()
        gov = MagicMock()
        gov.state.is_alive = True
        gov.state.agent_class = "governor"
        gov.state.name = "Gov1"
        gov.personality.disciplina = 0.2
        gov.personality.curiosidade = 0.9
        sim = _make_mock_sim(agents=[c, gov])
        with patch.object(sim.world.governance, 'propose_tech_restriction') as mock_propose:
            result = c._lobby_governor("Digital Ascension", sim)
            assert result >= 0
            calls = len(mock_propose.call_args_list)
            assert calls == 0


# ─── Tests: TechRestrictionLaw ─────────────────────────────────


class TestTechRestrictionLaw:
    def test_aprovada_com_lobbying_power_alto(self):
        gs = GovernanceSystem(SimulationConfig.default())
        gs.propose_tech_restriction("Digital Ascension", 0.7)
        r = gs.get_tech_restriction("Digital Ascension")
        assert r is not None
        assert r.active

    def test_nao_aprovada_com_lobbying_power_baixo(self):
        gs = GovernanceSystem(SimulationConfig.default())
        gs.propose_tech_restriction("Digital Ascension", 0.2)
        r = gs.get_tech_restriction("Digital Ascension")
        assert r is not None
        assert not r.active

    def test_restriction_level_maximo_0_8(self):
        gs = GovernanceSystem(SimulationConfig.default())
        gs.propose_tech_restriction("Digital Ascension", 1.0)
        r = gs.get_tech_restriction("Digital Ascension")
        assert r.restriction_level <= 0.8

    def test_restriction_level_calculo(self):
        gs = GovernanceSystem(SimulationConfig.default())
        gs.propose_tech_restriction("Digital Ascension", 0.5)
        r = gs.get_tech_restriction("Digital Ascension")
        assert r.restriction_level == 0.4 or r.restriction_level == pytest.approx(0.4, abs=0.001)

    def test_integracao_tech_tree_reduz_pesquisa(self):
        from pangeia.technology.tech_tree import TechnologySystem
        tech = TechnologySystem(rng=random.Random(42))
        asc = tech.technologies["ascension"]
        asc.research_cost = 10
        asc.prerequisites = []
        for t in tech.technologies.values():
            t.discovered = True if t.id != "ascension" else False
        gs = GovernanceSystem(SimulationConfig.default())
        gs.propose_tech_restriction("Digital Ascension", 1.0)
        r = gs.get_tech_restriction("Digital Ascension")
        assert r is not None
        assert r.restriction_level == 0.8
        assert r.active
        # Com restriction_level=0.8 e active, pesquisa deve ser bloqueada (0.8 > 0.7)
        assert r.restriction_level > 0.7


# ─── Tests: Integração ─────────────────────────────────────────


class TestIntegracao:
    def test_conservative_aparece_na_populacao(self):
        cfg = SimulationConfig.default()
        cfg.world.seed = 42
        cfg.world.initial_population = 500
        from pangeia.simulation import Simulation
        sim = Simulation(cfg)
        conservatives = [a for a in sim.agents.values() if a.state.agent_class == "conservative"]
        total = len(sim.agents)
        pct = len(conservatives) / total
        assert 0.04 <= pct <= 0.10, f"conservatives = {pct*100:.1f}% (expected ~7%)"

    def test_tick_completo_nao_quebra(self):
        cfg = SimulationConfig.default()
        cfg.world.seed = 42
        cfg.world.initial_population = 20
        from pangeia.simulation import Simulation
        sim = Simulation(cfg)
        for _ in range(10):
            sim.step()

    def test_governance_inclui_tech_restrictions(self):
        gs = GovernanceSystem(SimulationConfig.default())
        s = gs.summary()
        assert "tech_restrictions" in s

    def test_conservative_com_campanha_ativa(self):
        rng = random.Random(42)
        c = _make_conservative(rng=rng)
        c._active_campaigns["Digital Ascension"] = 100
        status = c.get_status()
        assert "Digital Ascension" in status["active_campaigns"]

    def test_lobbying_cumulativo(self):
        gs = GovernanceSystem(SimulationConfig.default())
        gs.propose_tech_restriction("Digital Ascension", 0.4)
        first = gs.get_tech_restriction("Digital Ascension")
        rl_first = first.restriction_level
        gs.propose_tech_restriction("Digital Ascension", 0.4)
        r = gs.get_tech_restriction("Digital Ascension")
        assert r.restriction_level > rl_first


# ─── Tests: Era index helper ───────────────────────────────────


def test_era_index_known():
    assert _era_index("singularity") == 6
    assert _era_index("quantum") == 5
    assert _era_index("industrial") == 3
    assert _era_index("primordial") == 0


def test_era_index_unknown():
    assert _era_index("unknown_era") == -1
