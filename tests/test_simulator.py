"""Unit tests for the deterministic OneCall AI simulation."""

import unittest

from demo.simulator import load_datasets, simulate_scenario


class SimulatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datasets = load_datasets()

    def simulate(self, scenario_id):
        return simulate_scenario(scenario_id, self.datasets)

    def test_scenario_1_location_mismatch(self):
        state = self.simulate("SCN001")
        self.assertEqual(
            state["root_cause"], "AUTHORIZATION_CLAIM_LOCATION_MISMATCH"
        )

    def test_scenario_1_calls_provider_agent(self):
        state = self.simulate("SCN001")
        self.assertIn("Provider Agent", state["agents_called"])

    def test_scenario_2_missing_authorization(self):
        state = self.simulate("SCN002")
        self.assertEqual(state["root_cause"], "PRIOR_AUTHORIZATION_MISSING")

    def test_scenario_2_skips_provider_agent(self):
        state = self.simulate("SCN002")
        self.assertNotIn("Provider Agent", state["agents_called"])

    def test_scenario_3_eligibility_enrollment_mismatch(self):
        state = self.simulate("SCN003")
        self.assertEqual(state["root_cause"], "ELIGIBILITY_ENROLLMENT_MISMATCH")

    def test_scenario_4_records_tool_errors(self):
        state = self.simulate("SCN004")
        self.assertGreaterEqual(len(state["tool_errors"]), 1)

    def test_scenario_4_records_alternate_lookup_recovery(self):
        state = self.simulate("SCN004")
        recovered_events = [
            event
            for event in state["investigation_trace"]
            if event["agent"] == "Authorization Agent"
            and event["status"] == "RECOVERED"
        ]
        self.assertGreaterEqual(len(recovered_events), 1)
        self.assertEqual(
            state["authorization"]["lookup_method"],
            "ALTERNATE_MEMBER_SERVICE_DATE",
        )

    def test_scenario_4_claim_link_failure(self):
        state = self.simulate("SCN004")
        self.assertEqual(state["root_cause"], "AUTHORIZATION_CLAIM_LINK_FAILURE")

    def test_every_scenario_recommends_an_action(self):
        for scenario in self.datasets["scenarios"]:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                state = self.simulate(scenario["scenario_id"])
                self.assertNotIn(state["recommended_action"], (None, "", "UNRESOLVED"))

    def test_no_scenario_performs_an_external_write(self):
        for scenario in self.datasets["scenarios"]:
            with self.subTest(scenario_id=scenario["scenario_id"]):
                state = self.simulate(scenario["scenario_id"])
                self.assertFalse(state["human_approval"]["external_write_performed"])


if __name__ == "__main__":
    unittest.main()
