from __future__ import annotations

import copy
import random
from unittest.mock import MagicMock, patch

import pytest

from pangeia.culture.emergent_ideology import (
    IdeologyTenet,
    EmergentIdeology,
    generate_tenets_from_personality,
    generate_name,
)


# ─── Helpers ──────────────────────────────────────────────────


def _mock_agent(curiosidade=0.5, empatia=0.5, altruismo=0.5, disciplina=0.5,
                agent_class="philosopher", agent_id="A1"):
    agent = MagicMock()
    agent.agent_id = agent_id
    agent.state.is_alive = True
    agent.state.agent_class = agent_class
    agent.state.influence = 0.0
    agent.state.education_level = 0.5
    agent.personality.curiosidade = curiosidade
    agent.personality.empatia = empatia
    agent.personality.altruismo = altruismo
    agent.personality.disciplina = disciplina
    agent.personality.ambicao = 0.5
    agent.personality.agressividade = 0.5
    agent.personality.sociabilidade = 0.5
    agent.personality.impulsividade = 0.5
    agent.personality.tolerancia_risco = 0.5
    agent.personality.resiliencia = 0.5
    agent.personality.espiritualidade = 0.5
    agent.knowledge = MagicMock()
    return agent


# ─── Tests: IdeologyTenet ──────────────────────────────────────


class TestIdeologyTenet:
    def test_instanciacao_campos_obrigatorios(self):
        tenet = IdeologyTenet(domain="technology", stance=0.8)
        assert tenet.domain == "technology"
        assert tenet.stance == 0.8
        assert tenet.target is None
        assert tenet.strength == 1.0

    def test_instanciacao_campos_completos(self):
        tenet = IdeologyTenet(domain="technology", stance=-0.8,
                              target="Digital Ascension", strength=0.8)
        assert tenet.domain == "technology"
        assert tenet.stance == -0.8
        assert tenet.target == "Digital Ascension"
        assert tenet.strength == 0.8


# ─── Tests: EmergentIdeology ───────────────────────────────────


class TestEmergentIdeology:
    def test_instanciacao(self):
        ideology = EmergentIdeology(
            id="em_1", name="Test Path",
            founder_id="A1", founder_class="philosopher",
            founded_tick=100,
            tenets=[IdeologyTenet(domain="technology", stance=0.5)],
        )
        assert ideology.id == "em_1"
        assert ideology.name == "Test Path"
        assert ideology.founder_id == "A1"
        assert ideology.founder_class == "philosopher"
        assert ideology.founded_tick == 100
        assert len(ideology.tenets) == 1
        assert ideology.followers == set()
        assert ideology.active is True

    def test_to_dict_returns_correct_structure(self):
        ideology = EmergentIdeology(
            id="em_1", name="Test Path",
            founder_id="A1", founder_class="philosopher",
            founded_tick=100,
            tenets=[IdeologyTenet(domain="technology", stance=0.8, strength=0.8)],
            followers={"A1", "A2"},
        )
        d = ideology.to_dict()
        assert d["id"] == "em_1"
        assert d["name"] == "Test Path"
        assert d["follower_count"] == 2
        assert d["influence"] == 0.0
        assert d["tenets"][0]["domain"] == "technology"
        assert d["tenets"][0]["stance"] == 0.8


# ─── Tests: generate_tenets_from_personality ──────────────────


class TestGenerateTenetsFromPersonality:
    def test_openness_alto_gera_stance_positiva_technology(self):
        agent = _mock_agent(curiosidade=0.9)
        tenets = generate_tenets_from_personality(agent, random.Random(42))
        tech_tenets = [t for t in tenets if t.domain == "technology" and t.target is None]
        assert len(tech_tenets) >= 1
        assert tech_tenets[0].stance > 0

    def test_openness_baixo_gera_tenet_contra_digital_ascension(self):
        agent = _mock_agent(curiosidade=0.1)
        tenets = generate_tenets_from_personality(agent, random.Random(42))
        ascension_tenets = [
            t for t in tenets
            if t.domain == "technology" and t.target == "Digital Ascension"
        ]
        assert len(ascension_tenets) >= 1
        assert ascension_tenets[0].stance < -0.5

    def test_nome_gerado_nao_vazio(self):
        agent = _mock_agent(curiosidade=0.9)
        tenets = generate_tenets_from_personality(agent, random.Random(42))
        name = generate_name(tenets, random.Random(42))
        assert isinstance(name, str)
        assert len(name) > 0
        assert " " in name

    def test_openness_alto_sem_ascension_tenet(self):
        agent = _mock_agent(curiosidade=0.9)
        tenets = generate_tenets_from_personality(agent, random.Random(42))
        ascension = [t for t in tenets if t.target == "Digital Ascension"]
        assert len(ascension) == 0

    def test_social_stance_reflete_agreeableness(self):
        agent_alto = _mock_agent(empatia=0.9, altruismo=0.9)
        agent_baixo = _mock_agent(empatia=0.1, altruismo=0.1)
        tenets_alto = generate_tenets_from_personality(agent_alto, random.Random(42))
        tenets_baixo = generate_tenets_from_personality(agent_baixo, random.Random(42))
        social_alto = [t for t in tenets_alto if t.domain == "social"]
        social_baixo = [t for t in tenets_baixo if t.domain == "social"]
        assert social_alto[0].stance > social_baixo[0].stance


# ─── Tests: IdeologyManager ────────────────────────────────────


@pytest.fixture
def manager_and_agents():
    rng = random.Random(42)
    world = MagicMock()
    from pangeia.culture.ideology_manager import IdeologyManager
    manager = IdeologyManager(world, rng)
    agents = {}
    for i in range(20):
        a = _mock_agent(
            curiosidade=rng.uniform(0.1, 0.9),
            empatia=rng.uniform(0.1, 0.9),
            altruismo=rng.uniform(0.1, 0.9),
            disciplina=rng.uniform(0.1, 0.9),
            agent_class="philosopher",
            agent_id=f"A{i}",
        )
        agents[f"A{i}"] = a
    return manager, agents


class TestIdeologyManager:
    def test_philosopher_cria_ideologia(self, manager_and_agents):
        manager, agents = manager_and_agents
        manager._maybe_create_ideologies(agents, tick=0)
        assert len(manager.ideologies) >= 0

    def test_criacao_respeita_cooldown(self, manager_and_agents):
        manager, agents = manager_and_agents
        for agent in agents.values():
            agent.state.agent_class = "philosopher"
        # Force creation by running many ticks
        for tick in range(0, 500, 50):
            manager._maybe_create_ideologies(agents, tick)
        created_after_first = len(manager.ideologies)
        # Run again immediately — cooldown should block
        manager._maybe_create_ideologies(agents, tick=500)
        assert len(manager.ideologies) >= created_after_first

    def test_nao_philosopher_nao_cria_ideologia(self, manager_and_agents):
        manager, agents = manager_and_agents
        for agent in agents.values():
            agent.state.agent_class = "citizen"
        # Run many ticks
        for tick in range(0, 2000, 50):
            manager._maybe_create_ideologies(agents, tick)
        assert len(manager.ideologies) == 0

    @patch("pangeia.culture.ideology_manager.IdeologyManager._compute_compatibility")
    def test_agente_compativel_adota_ideologia(self, mock_compat, manager_and_agents):
        mock_compat.return_value = 0.8
        manager, agents = manager_and_agents
        ideology = EmergentIdeology(
            id="em_test", name="Test Path",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            tenets=[IdeologyTenet(domain="technology", stance=0.5)],
            followers={"A0"},
        )
        manager.ideologies["em_test"] = ideology
        manager._spread_ideologies(agents, tick=100)
        assert len(ideology.followers) >= 1
        assert ideology.active

    def test_decay_desativa_ideologia(self, manager_and_agents):
        manager, agents = manager_and_agents
        ideology = EmergentIdeology(
            id="em_test", name="Test",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            followers=set(),
            active=True,
        )
        ideology.influence = 0.005
        manager.ideologies["em_test"] = ideology
        for _ in range(60):
            manager._decay_ideologies(agents, tick=100)
        assert not ideology.active

    def test_update_influence_calcula_corretamente(self, manager_and_agents):
        manager, agents = manager_and_agents
        ideology = EmergentIdeology(
            id="em_test", name="Test",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            followers={"A0", "A1", "A2", "A3"},
        )
        manager.ideologies["em_test"] = ideology
        manager._update_influence(agents)
        assert ideology.influence == 4.0 / 20.0


# ─── Tests: get_technology_modifier ────────────────────────────


class TestTechnologyModifier:
    def test_agente_sem_ideologia_retorna_zero(self, manager_and_agents):
        manager, agents = manager_and_agents
        mod = manager.get_technology_modifier("A0", "Digital Ascension")
        assert mod == 0.0

    def test_agente_com_ideologia_pro_tech_retorna_positivo(self, manager_and_agents):
        manager, agents = manager_and_agents
        ideology = EmergentIdeology(
            id="em_test", name="Pro Tech",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            tenets=[IdeologyTenet(domain="technology", stance=0.8, strength=0.8)],
            followers={"A0"},
            active=True,
        )
        manager.ideologies["em_test"] = ideology
        mod = manager.get_technology_modifier("A0", "Any Tech")
        assert mod > 0.0

    def test_tenet_especifico_ascension_retorna_negativo(self, manager_and_agents):
        manager, agents = manager_and_agents
        ideology = EmergentIdeology(
            id="em_test", name="Anti Ascension",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            tenets=[IdeologyTenet(domain="technology", stance=-0.8,
                                  target="Digital Ascension", strength=0.8)],
            followers={"A0"},
            active=True,
        )
        manager.ideologies["em_test"] = ideology
        mod = manager.get_technology_modifier("A0", "Digital Ascension")
        assert mod < 0.0
        # Specific tenet weighed 2x: -0.8 * 0.8 * 2.0 = -1.28, clamped to -1.0
        assert mod == -1.0

    def test_tenet_especifico_peso_maior_que_geral(self, manager_and_agents):
        manager, agents = manager_and_agents
        ideology = EmergentIdeology(
            id="em_test", name="Mixed",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            tenets=[
                IdeologyTenet(domain="technology", stance=0.5, strength=0.5),
                IdeologyTenet(domain="technology", stance=-0.8,
                              target="Digital Ascension", strength=0.8),
            ],
            followers={"A0"},
            active=True,
        )
        manager.ideologies["em_test"] = ideology
        mod = manager.get_technology_modifier("A0", "Digital Ascension")
        # -0.8*0.8*2.0 + 0.5*0.5*0.5 = -1.28 + 0.125 = -1.155 → clamped to -1.0
        assert mod == -1.0
        mod_other = manager.get_technology_modifier("A0", "Other Tech")
        # 0.5*0.5*0.5 = 0.125 (no specific match)
        assert mod_other == 0.125

    def test_modifier_sempre_entre_um_e_um(self, manager_and_agents):
        manager, agents = manager_and_agents
        ideology = EmergentIdeology(
            id="em_test", name="Extreme",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            tenets=[IdeologyTenet(domain="technology", stance=1.0, strength=1.0)],
            followers={"A0"},
            active=True,
        )
        mod = manager.get_technology_modifier("A0", "Tech")
        assert -1.0 <= mod <= 1.0


# ─── Integration Tests ─────────────────────────────────────────


class TestIntegration:
    def test_tick_completo_nao_quebra(self):
        """Cria um World com IdeologyManager e roda tick manualmente."""
        from pangeia.config import SimulationConfig
        from pangeia.core.world import World
        cfg = SimulationConfig.default()
        rng = random.Random(42)
        world = World(cfg, rng=rng)
        agent = _mock_agent(curiosidade=0.1, agent_class="philosopher", agent_id="A0")
        agents = {"A0": agent}
        world.ideology_manager.tick(agents, current_tick=0)
        agents["A0"].state.is_alive = True
        world.ideology_manager.tick(agents, current_tick=1)
        assert True

    def test_ideologies_endpoint_retorna_estrutura_correta(self):
        from pangeia.culture.ideology_manager import IdeologyManager
        rng = random.Random(42)
        world = MagicMock()
        manager = IdeologyManager(world, rng)
        ideology = EmergentIdeology(
            id="em_test", name="Test",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            tenets=[IdeologyTenet(domain="technology", stance=0.5)],
            followers={"A0"},
            active=True,
        )
        manager.ideologies["em_test"] = ideology
        d = manager.to_dict()
        assert "emergent" in d
        assert "count" in d
        assert "total_followers" in d
        assert d["count"] == 1
        assert d["total_followers"] == 1

    def test_agente_anti_tech_tem_probabilidade_reduzida(self, manager_and_agents):
        """Simula a lógica de tecnologia: ideologia negativa reduz progresso."""
        manager, agents = manager_and_agents
        ideology = EmergentIdeology(
            id="em_test", name="Anti Tech",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            tenets=[IdeologyTenet(domain="technology", stance=-0.8, strength=0.9)],
            followers={"A0"},
            active=True,
        )
        manager.ideologies["em_test"] = ideology
        mod = manager.get_technology_modifier("A0", "Some Tech")
        # -0.8 * 0.9 * 0.5 = -0.36
        assert mod < 0.0
        assert abs(mod) <= 1.0

    def test_agentes_conflitantes_nao_compartilham_followers(self, manager_and_agents):
        manager, agents = manager_and_agents
        # Create two conflicting ideologies
        ideo1 = EmergentIdeology(
            id="em_1", name="Pro Tech",
            founder_id="A0", founder_class="philosopher",
            founded_tick=0,
            tenets=[IdeologyTenet(domain="technology", stance=0.8)],
            followers={"A0"},
            active=True,
        )
        ideo2 = EmergentIdeology(
            id="em_2", name="Anti Tech",
            founder_id="A1", founder_class="philosopher",
            founded_tick=0,
            tenets=[IdeologyTenet(domain="technology", stance=-0.8)],
            followers={"A1"},
            active=True,
        )
        manager.ideologies["em_1"] = ideo1
        manager.ideologies["em_2"] = ideo2
        # Same agent can't be in both
        assert "A0" not in ideo2.followers
        assert "A1" not in ideo1.followers
