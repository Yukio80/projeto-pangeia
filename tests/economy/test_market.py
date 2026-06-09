"""Testes do subsistema de Economia."""


class TestEconomy:
    def test_step_updates_gdp(self, small_simulation):
        sim = small_simulation
        for _ in range(20):
            sim.step()
        summary = sim.economy.summary()
        indicators = summary["indicators"]
        assert "gdp" in indicators
        assert indicators["gdp"] > 0, "GDP should grow after ticks"

    def test_inequality_bounded(self, small_simulation):
        sim = small_simulation
        for _ in range(100):
            sim.step()
        summary = sim.economy.summary()
        indicators = summary["indicators"]
        assert "inequality" in indicators
        assert 0 <= indicators["inequality"] <= 1, "Inequality out of [0,1]"

    def test_companies_form(self, small_simulation):
        sim = small_simulation
        for _ in range(50):
            sim.step()
        summary = sim.economy.summary()
        assert summary["companies"] >= 0

    def test_prices_exist(self, small_simulation):
        sim = small_simulation
        for _ in range(30):
            sim.step()
        prices = sim.economy.summary()["prices"]
        assert isinstance(prices, dict)

    def test_company_startup_cost_respected(self, small_simulation):
        sim = small_simulation
        for _ in range(20):
            sim.step()
        cfg = sim.config
        cost = cfg.economy.company_startup_cost
        poor_agents = [a for a in sim.agents.values()
                       if a.state.wealth < cost]
        for a in poor_agents:
            assert all(c.owner_id != a.agent_id for c in sim.economy.companies.values())

    def test_indicators_have_all_keys(self, small_simulation):
        sim = small_simulation
        for _ in range(20):
            sim.step()
        ind = sim.economy.summary()["indicators"]
        expected = {"gdp", "inequality", "tech_level", "productivity",
                    "employment", "inflation", "trade_volume"}
        for k in expected:
            assert k in ind, f"Key {k} missing from indicators"
