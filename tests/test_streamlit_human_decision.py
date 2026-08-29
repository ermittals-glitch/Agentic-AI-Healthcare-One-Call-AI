"""Streamlit AppTest coverage for the representative decision state machine."""

from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "streamlit_app.py"
APPROVE_BUTTON = "Approve recommended action"
ESCALATE_BUTTON = "Escalate for specialist review"
CHANGE_BUTTON = "Change representative decision"


class HumanDecisionAppTests(unittest.TestCase):
    maxDiff = None

    def start_scenario(self, scenario_id: str) -> AppTest:
        app = AppTest.from_file(str(APP_PATH), default_timeout=20).run()
        self.assertFalse(app.exception)
        app.selectbox[0].set_value(scenario_id).run()
        self.button(app, "Start resolution").click().run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state["representative_decision"], None)
        self.assertEqual(
            app.session_state["post_decision_case_status"],
            "AWAITING_HUMAN_APPROVAL",
        )
        return app

    @staticmethod
    def button(app: AppTest, label: str):
        return next(button for button in app.button if button.label == label)

    @staticmethod
    def button_labels(app: AppTest) -> set[str]:
        return {button.label for button in app.button}

    @staticmethod
    def visible_text(app: AppTest) -> str:
        values: list[str] = []
        for element_type in (
            "success",
            "warning",
            "info",
            "markdown",
            "caption",
            "subheader",
        ):
            for element in app.get(element_type):
                value = getattr(element, "value", None)
                if value is not None:
                    values.append(str(value))
        return "\n".join(values)

    @staticmethod
    def metrics(app: AppTest) -> dict[str, str]:
        return {metric.label: str(metric.value) for metric in app.metric}

    def assert_decision_outcome(
        self,
        scenario_id: str,
        decision: str,
        expected_status: str,
        expected_headline: str,
        expected_action_or_queue: str,
        expected_message: str,
    ) -> None:
        app = self.start_scenario(scenario_id)
        label = APPROVE_BUTTON if decision == "APPROVED" else ESCALATE_BUTTON
        self.button(app, label).click().run()
        self.assertFalse(app.exception)

        state = app.session_state["case_state"]
        self.assertEqual(app.session_state["representative_decision"], decision)
        self.assertEqual(
            app.session_state["post_decision_case_status"], expected_status
        )
        self.assertEqual(state["current_status"], expected_status)
        self.assertFalse(state["member_transfer_required"])
        self.assertFalse(state["human_approval"]["external_write_performed"])

        labels = self.button_labels(app)
        self.assertNotIn(APPROVE_BUTTON, labels)
        self.assertNotIn(ESCALATE_BUTTON, labels)
        self.assertIn(CHANGE_BUTTON, labels)

        text = self.visible_text(app)
        self.assertIn(expected_headline, text)
        self.assertIn(expected_action_or_queue, text)
        self.assertIn(expected_message, text)
        self.assertIn("Payer record modified:** No", text)
        if decision == "APPROVED":
            self.assertIn(
                f"Representative approved {state['recommended_action']}", text
            )
            self.assertIn("Case] **Ready for action", text)
        if decision == "ESCALATED":
            self.assertIn("internal case handoff", text)
            self.assertIn("Representative requested specialist review", text)
            self.assertIn("Shared case evidence preserved", text)
            self.assertNotIn("Member transferred to specialist", text)

        metrics = self.metrics(app)
        self.assertEqual(metrics["Member transfer required"], "No")
        self.assertEqual(metrics["Member must repeat issue"], "No")
        self.assertEqual(metrics["Shared case context"], "Preserved")

    def test_scn001_approved(self):
        self.assert_decision_outcome(
            "SCN001",
            "APPROVED",
            "READY_FOR_ACTION",
            "Claim reconsideration ready for action",
            "Claim reconsideration",
            "Representative approved preparation of claim reconsideration",
        )

    def test_scn001_escalated(self):
        self.assert_decision_outcome(
            "SCN001",
            "ESCALATED",
            "HUMAN_REVIEW_REQUIRED",
            "Claims and Authorization specialist review requested",
            "Claims + Authorization Review",
            "location mismatch before proceeding with reconsideration",
        )

    def test_scn002_approved(self):
        self.assert_decision_outcome(
            "SCN002",
            "APPROVED",
            "READY_FOR_ACTION",
            "Provider authorization follow-up ready",
            "Provider initiate authorization",
            "no applicable authorization was found",
        )

    def test_scn002_escalated(self):
        self.assert_decision_outcome(
            "SCN002",
            "ESCALATED",
            "HUMAN_REVIEW_REQUIRED",
            "Authorization specialist review requested",
            "Authorization Review",
            "retro-authorization path",
        )

    def test_scn003_approved(self):
        self.assert_decision_outcome(
            "SCN003",
            "APPROVED",
            "READY_FOR_ACTION",
            "Eligibility record review ready",
            "Eligibility record review",
            "active enrollment evidence",
        )

    def test_scn003_escalated(self):
        self.assert_decision_outcome(
            "SCN003",
            "ESCALATED",
            "HUMAN_REVIEW_REQUIRED",
            "Eligibility and Enrollment specialist review requested",
            "Eligibility + Enrollment Review",
            "enrollment/eligibility synchronization discrepancy",
        )

    def test_scn004_approved(self):
        self.assert_decision_outcome(
            "SCN004",
            "APPROVED",
            "READY_FOR_ACTION",
            "Recovered authorization evidence ready for claim reconsideration",
            "Claim reconsideration",
            "alternate lookup strategy",
        )
        app = self.start_scenario("SCN004")
        self.button(app, APPROVE_BUTTON).click().run()
        metrics = self.metrics(app)
        self.assertEqual(metrics["Primary authorization lookup"], "Failed")
        self.assertEqual(metrics["Retry"], "Failed")
        self.assertEqual(metrics["Alternate lookup"], "Success")
        self.assertEqual(metrics["Authorization recovered"], "Yes")

    def test_scn004_escalated(self):
        self.assert_decision_outcome(
            "SCN004",
            "ESCALATED",
            "HUMAN_REVIEW_REQUIRED",
            "Claims and Authorization specialist review requested",
            "Claims + Authorization Review",
            "original authorization lookup path failed",
        )

    def test_scenario_change_resets_decision_and_prior_case(self):
        app = self.start_scenario("SCN001")
        self.button(app, APPROVE_BUTTON).click().run()
        app.selectbox[0].set_value("SCN002").run()
        self.assertEqual(app.session_state["representative_decision"], None)
        self.assertEqual(
            app.session_state["post_decision_case_status"],
            "AWAITING_HUMAN_APPROVAL",
        )
        self.assertEqual(app.session_state["case_state"], None)

    def test_new_resolution_resets_decision(self):
        app = self.start_scenario("SCN001")
        self.button(app, APPROVE_BUTTON).click().run()
        self.button(app, "Start resolution").click().run()
        self.assertEqual(app.session_state["representative_decision"], None)
        self.assertEqual(
            app.session_state["post_decision_case_status"],
            "AWAITING_HUMAN_APPROVAL",
        )
        labels = self.button_labels(app)
        self.assertIn(APPROVE_BUTTON, labels)
        self.assertIn(ESCALATE_BUTTON, labels)

    def test_change_decision_returns_to_awaiting_approval(self):
        app = self.start_scenario("SCN001")
        self.button(app, APPROVE_BUTTON).click().run()
        original_trace = list(app.session_state["case_state"]["investigation_trace"])
        self.button(app, CHANGE_BUTTON).click().run()
        self.assertEqual(app.session_state["representative_decision"], None)
        self.assertEqual(
            app.session_state["post_decision_case_status"],
            "AWAITING_HUMAN_APPROVAL",
        )
        self.assertEqual(
            app.session_state["case_state"]["current_status"],
            "AWAITING_HUMAN_APPROVAL",
        )
        self.assertEqual(
            app.session_state["case_state"]["investigation_trace"], original_trace
        )
        labels = self.button_labels(app)
        self.assertIn(APPROVE_BUTTON, labels)
        self.assertIn(ESCALATE_BUTTON, labels)


if __name__ == "__main__":
    unittest.main()
