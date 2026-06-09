"""Testes do subsistema de Tecnologia."""

import pytest
from pangeia.technology.tech_tree import TechnologySystem


class TestTechnology:
    def test_initial_state(self, tech):
        summary = tech.summary()
        assert "total_technologies" in summary
        assert "era" in summary
        assert summary["total_technologies"] > 0

    def test_get_era(self, tech):
        era = tech.get_era()
        assert isinstance(era, str)
        assert len(era) > 0

    def test_get_tech_level(self, tech):
        level = tech.get_tech_level()
        assert 0 <= level <= 1

    def test_can_research_prerequisites(self, tech):
        for t in tech.technologies.values():
            if t.prerequisites:
                can = tech.can_research(t.id)
                if not all(p in tech.technologies and tech.technologies[p].discovered
                          for p in t.prerequisites):
                    assert not can, f"{t.id} should not be researchable without prerequisites"

    def test_can_research_foundational(self, tech):
        for t in tech.technologies.values():
            if not t.prerequisites and not t.discovered:
                assert tech.can_research(t.id), f"{t.id} should be researchable"

    def test_research_discovers(self, tech):
        for t in tech.technologies.values():
            if tech.can_research(t.id):
                result = tech.research(t.id, t.research_cost)
                if result:
                    assert tech.technologies[t.id].discovered
                break

    def test_step_advances_research(self, small_simulation):
        sim = small_simulation
        initial = sim.technology.get_tech_level()
        for _ in range(100):
            sim.step()
        final = sim.technology.get_tech_level()
        assert final >= initial, "Tech level should not decrease"

    def test_researchable_cache(self, tech):
        tech._researchable_cache = None
        r1 = tech.get_researchable()
        r2 = tech.get_researchable()
        assert len(r1) == len(r2)

    def test_no_out_of_order_discoveries(self, small_simulation):
        sim = small_simulation
        for _ in range(200):
            sim.step()
        for t in sim.technology.technologies.values():
            if t.discovered:
                for prereq in t.prerequisites:
                    assert sim.technology.technologies[prereq].discovered, (
                        f"{t.name} discovered without prerequisite {prereq}"
                    )

    def test_knowledge_spreads(self, small_simulation):
        sim = small_simulation
        for _ in range(100):
            sim.step()
        total_spread = sum(t.spread for t in sim.technology.technologies.values())
        assert total_spread >= 0

    def test_summary_has_era(self, tech):
        summary = tech.summary()
        assert "era" in summary
        assert "tech_level" in summary
        assert "discovered" in summary
