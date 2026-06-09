"""Testes do subsistema de Governança."""


class TestGovernance:
    def test_register_voter(self, governance):
        governance.register_voter("A001")

    def test_step_updates_stability(self, small_simulation):
        sim = small_simulation
        for _ in range(50):
            sim.step()
        gov = sim.governance.summary()
        stability = gov["government"]["stability"]
        assert 0 <= stability <= 1

    def test_laws_accumulate(self, small_simulation):
        sim = small_simulation
        for _ in range(50):
            sim.step()
        gov = sim.governance.summary()
        assert isinstance(gov["government"]["laws"], int)
        assert gov["government"]["laws"] >= 0

    def test_hold_election(self, small_simulation):
        sim = small_simulation
        for _ in range(30):
            sim.step()
        sim.governance.hold_election(sim.agents, sim.world.state.tick)
        gov = sim.governance.summary()
        assert gov["government"]["stability"] > 0

    def test_government_type_string(self, small_simulation):
        sim = small_simulation
        for _ in range(50):
            sim.step()
        gov = sim.governance.summary()
        assert isinstance(gov["government"]["type"], str)

    def test_government_summary_has_all_keys(self, small_simulation):
        sim = small_simulation
        for _ in range(50):
            sim.step()
        gov = sim.governance.summary()
        assert "government" in gov
        assert "voters" in gov
        assert "election_cycle" in gov
        assert "term_tick" in gov
