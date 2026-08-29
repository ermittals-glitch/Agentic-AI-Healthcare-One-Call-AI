"""OneCall AI call-center console for validated scenario playback."""

from __future__ import annotations

from typing import Any

import streamlit as st

from demo.simulator import SimulationDataError, load_datasets, simulate_scenario


st.set_page_config(
    page_title="OneCall AI | Healthcare resolution copilot",
    page_icon=":material/health_and_safety:",
    layout="wide",
)


AWAITING_HUMAN_APPROVAL = "AWAITING_HUMAN_APPROVAL"
READY_FOR_ACTION = "READY_FOR_ACTION"
HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"
DECISION_TO_STATUS = {
    None: AWAITING_HUMAN_APPROVAL,
    "APPROVED": READY_FOR_ACTION,
    "ESCALATED": HUMAN_REVIEW_REQUIRED,
}

REPRESENTATIVE_OUTCOMES: dict[str, dict[str, dict[str, Any]]] = {
    "SCN001": {
        "APPROVED": {
            "headline": "Claim reconsideration ready for action",
            "action": "CLAIM_RECONSIDERATION",
            "explanation": (
                "Representative approved preparation of claim reconsideration using "
                "the approved authorization and the identified claim/authorization "
                "servicing-location mismatch."
            ),
            "evidence": [
                "Denied claim",
                "Approved authorization",
                "Claim servicing location",
                "Authorization servicing location",
                "Same provider organization",
                "In-network validation",
            ],
            "member_action_required": "None",
            "representative_ownership": "Yes",
        },
        "ESCALATED": {
            "headline": "Claims and Authorization specialist review requested",
            "specialist_queue": "Claims + Authorization Review",
            "reason": (
                "Representative requested additional review of the claim/authorization "
                "location mismatch before proceeding with reconsideration."
            ),
            "evidence": "Claim + authorization + provider/location findings",
        },
    },
    "SCN002": {
        "APPROVED": {
            "headline": "Provider authorization follow-up ready",
            "action": "PROVIDER_INITIATE_AUTHORIZATION",
            "explanation": (
                "Representative approved provider follow-up because the covered MRI "
                "requires prior authorization and no applicable authorization was found."
            ),
            "operational_next_step": (
                "Provider should initiate the required prior-authorization process "
                "before claim resolution can proceed."
            ),
        },
        "ESCALATED": {
            "headline": "Authorization specialist review requested",
            "specialist_queue": "Authorization Review",
            "reason": (
                "Representative requested specialist review to confirm whether an "
                "exception, retro-authorization path, or additional authorization "
                "review is appropriate."
            ),
            "evidence": (
                "Eligibility + benefit requirement + denied claim + authorization "
                "NOT_FOUND"
            ),
        },
    },
    "SCN003": {
        "APPROVED": {
            "headline": "Eligibility record review ready",
            "action": "ELIGIBILITY_RECORD_REVIEW",
            "explanation": (
                "Representative approved internal eligibility record review using the "
                "active enrollment evidence and the conflicting inactive servicing "
                "eligibility record."
            ),
            "operational_next_step": (
                "Enrollment and servicing eligibility records are ready for internal "
                "reconciliation."
            ),
        },
        "ESCALATED": {
            "headline": "Eligibility and Enrollment specialist review requested",
            "specialist_queue": "Eligibility + Enrollment Review",
            "reason": (
                "Representative requested specialist review of the enrollment/"
                "eligibility synchronization discrepancy."
            ),
            "evidence": (
                "Enrollment status + effective date + servicing eligibility state + "
                "synchronization evidence"
            ),
        },
    },
    "SCN004": {
        "APPROVED": {
            "headline": (
                "Recovered authorization evidence ready for claim reconsideration"
            ),
            "action": "CLAIM_RECONSIDERATION",
            "explanation": (
                "Representative approved claim reconsideration after OneCall AI "
                "recovered the authorization through an alternate lookup strategy."
            ),
            "show_recovery": True,
        },
        "ESCALATED": {
            "headline": "Claims and Authorization specialist review requested",
            "specialist_queue": "Claims + Authorization Review",
            "reason": (
                "Representative requested specialist review despite successful "
                "authorization recovery because the original authorization lookup "
                "path failed."
            ),
            "evidence": [
                "Primary lookup failure",
                "Retry failure",
                "Alternate lookup selected",
                "Recovered authorization",
                "Claim evidence",
            ],
        },
    },
}


@st.cache_data
def get_demo_data() -> dict[str, list[dict[str, Any]]]:
    """Load the repository's synthetic, validated scenario fixtures."""

    return load_datasets()


def humanize(value: Any) -> str:
    """Format workflow enum values for representative-facing display."""

    if value in (None, ""):
        return "Not applicable"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    return str(value).replace("_", " ").capitalize()


def apply_representative_state(case_state: dict[str, Any]) -> None:
    """Project the UI-only representative decision onto the displayed case state."""

    decision = st.session_state.representative_decision
    if decision not in DECISION_TO_STATUS:
        decision = None
    case_state["current_status"] = DECISION_TO_STATUS[decision]
    case_state["human_approval"]["status"] = decision or "PENDING"
    case_state["human_approval"]["external_write_performed"] = False
    st.session_state.post_decision_case_status = DECISION_TO_STATUS[decision]


def reset_representative_decision(*, clear_case: bool = False) -> None:
    """Clear only the human choice and restore the awaiting-approval boundary."""

    st.session_state.representative_decision = None
    st.session_state.post_decision_case_status = AWAITING_HUMAN_APPROVAL
    case_state = st.session_state.get("case_state")
    if case_state:
        apply_representative_state(case_state)
    if clear_case:
        st.session_state.case_state = None
        st.session_state.investigated_scenario_id = None


def reset_case_for_scenario() -> None:
    """Reset the decision and prior playback when the demo scenario changes."""

    reset_representative_decision(clear_case=True)


def select_representative_decision(decision: str) -> None:
    """Persist one validated representative choice without performing a payer write."""

    if decision not in {"APPROVED", "ESCALATED"}:
        raise ValueError(f"Unsupported representative decision: {decision}")
    st.session_state.representative_decision = decision
    case_state = st.session_state.get("case_state")
    if case_state:
        apply_representative_state(case_state)


def scenario_intake(
    scenario: dict[str, Any], datasets: dict[str, list[dict[str, Any]]]
) -> dict[str, str]:
    """Return the supported intake fields for one validated scenario."""

    claim = next(
        (
            item
            for item in datasets["claims"]
            if item["claim_id"] == scenario.get("claim_id")
        ),
        None,
    )
    if claim:
        return {
            "member_id": scenario["member_id"],
            "service_code": claim["service"]["service_code"],
            "service_date": claim["service_date"],
        }

    member = next(
        item
        for item in datasets["members"]
        if item["member_id"] == scenario["member_id"]
    )
    benefit = next(
        item
        for item in datasets["benefits"]
        if item["plan_id"] == member["plan_id"]
    )
    return {
        "member_id": scenario["member_id"],
        "service_code": benefit["service_code"],
        "service_date": "Not applicable",
    }


def render_status_badge(label: str, status: str) -> None:
    colors = {
        "Pending": "gray",
        "Running": "blue",
        "Complete": "green",
        "Escalated": "orange",
    }
    icons = {
        "Pending": ":material/schedule:",
        "Running": ":material/progress_activity:",
        "Complete": ":material/check:",
        "Escalated": ":material/support_agent:",
    }
    st.badge(f"{label} · {status}", color=colors[status], icon=icons[status])


def render_stage_progress(case_state: dict[str, Any] | None) -> None:
    """Show the bounded servicing flow as representative-facing status chips."""

    if case_state is None:
        stages = [
            ("Intake", "Pending"),
            ("Orchestrator", "Pending"),
            ("Tool checks", "Pending"),
            ("Evidence synthesis", "Pending"),
            ("Recommendation", "Pending"),
        ]
    else:
        final_status = (
            "Escalated"
            if case_state["human_approval"]["status"] == "ESCALATED"
            else "Complete"
        )
        stages = [
            ("Intake", "Complete"),
            ("Orchestrator", "Complete"),
            ("Tool checks", "Complete"),
            ("Evidence synthesis", "Complete"),
            ("Recommendation", final_status),
        ]

    columns = st.columns(len(stages), vertical_alignment="center")
    for column, (label, status) in zip(columns, stages):
        with column:
            render_status_badge(label, status)


def render_activity(activity: dict[str, Any]) -> None:
    styles = {
        "SUCCESS": ("green", ":material/check_circle:"),
        "RECOVERED": ("green", ":material/settings_backup_restore:"),
        "ERROR": ("red", ":material/error:"),
        "RETRY": ("orange", ":material/refresh:"),
        "HUMAN REVIEW": ("orange", ":material/person_check:"),
        "DECISION": ("blue", ":material/route:"),
    }
    color, icon = styles.get(activity["status"], ("gray", ":material/pending:"))
    st.markdown(
        f"{icon} :{color}-badge[{humanize(activity['status'])}] "
        f"**{activity['agent']}** — {activity['summary']}"
    )
    if activity.get("decision"):
        st.caption(f"Workflow decision: {humanize(activity['decision'])}")


def render_architecture() -> None:
    """Render the stable backend component boundary with native Mermaid support."""

    st.mermaid_chart(
        """
        flowchart LR
            INTAKE["Member interaction intake<br/>Streamlit agent console<br/>Call or chat<br/>Member explains issue once"]
            INTAKE --> MAIN["Main Orchestrator<br/>Shared case state"]
            MAIN <--> PLANNER["Orchestrator Agent"]
            PLANNER --> TOOLS["Deterministic domain tools<br/>Eligibility · Benefits · Claims<br/>Authorization · Provider"]
            TOOLS -->|Orchestrated system checks| MAIN
            MAIN --> RESOLUTION["Resolution Agent<br/>Evidence-based resolution"]
            RESOLUTION --> REVIEW["Human approval or review"]
            REVIEW --> OUTCOME["Final resolution<br/>Evidence returned to representative"]
            OUTCOME -->|One guided interaction| INTAKE
        """,
        width="stretch",
    )


def render_selected_path(case_state: dict[str, Any]) -> None:
    """Show only the agents and recovery steps actually used by the selected fixture."""

    st.caption("Selected case path · derived from the completed investigation trace")
    with st.container(horizontal=True, gap="small"):
        for agent in case_state["agents_called"]:
            st.badge(
                agent.replace(" Agent", ""),
                color="green",
                icon=":material/check:",
            )
    if case_state["tool_errors"]:
        st.warning(
            f"Authorization recovery activated: {len(case_state['tool_errors'])} "
            "primary lookup failures were recorded before alternate lookup succeeded.",
            icon=":material/settings_backup_restore:",
        )


def render_representative_orchestration_event(case_state: dict[str, Any]) -> None:
    """Append the human decision visually after the immutable AI/tool trace."""

    decision = st.session_state.representative_decision
    if decision == "APPROVED":
        st.markdown(
            ":orange-badge[Human review] **Representative approved "
            f"{case_state['recommended_action']}**"
        )
        st.markdown(":green-badge[Case] **Ready for action**")
    elif decision == "ESCALATED":
        st.markdown(
            ":orange-badge[Human review] **Representative requested specialist review**"
        )
        st.markdown(":orange-badge[Case] **Human review required**")
        st.markdown(":blue-badge[Context] **Shared case evidence preserved**")


def render_evidence_package(evidence: str | list[str]) -> None:
    """Render a human-readable evidence package from the UI outcome matrix."""

    if isinstance(evidence, list):
        for item in evidence:
            st.markdown(f"- {item}")
    else:
        st.write(evidence)


def render_recovery_evidence() -> None:
    """Make the validated SCN004 fallback path explicit after approval."""

    st.markdown("**Recovered authorization evidence**")
    columns = st.columns(4)
    columns[0].metric("Primary authorization lookup", "Failed")
    columns[1].metric("Retry", "Failed")
    columns[2].metric("Alternate lookup", "Success")
    columns[3].metric("Authorization recovered", "Yes")


def render_case_continuity(decision: str) -> None:
    """Show the member and write-safety guarantees for either decision path."""

    st.markdown("**Member and case continuity**")
    columns = st.columns(3)
    columns[0].metric("Member transfer required", "No")
    columns[1].metric("Member must repeat issue", "No")
    columns[2].metric("Shared case context", "Preserved")
    if decision == "APPROVED":
        st.write(
            "**Payer record modified:** No — recommendation staged only in this "
            "prototype."
        )
    else:
        st.write(
            "**Payer record modified:** No — evidence package prepared only in this "
            "prototype."
        )
        st.info(
            "Case routed for specialist review with shared context. This is an internal "
            "case handoff; the member remains in the current interaction.",
            icon=":material/forward_to_inbox:",
        )


def render_post_decision_result(case_state: dict[str, Any], scenario_id: str) -> None:
    """Render one explicit final representative-decision result card."""

    decision = st.session_state.representative_decision
    outcome = REPRESENTATIVE_OUTCOMES[scenario_id][decision]
    status = DECISION_TO_STATUS[decision]
    decision_label = "Approved" if decision == "APPROVED" else "Specialist review requested"

    with st.container(border=True):
        if decision == "APPROVED":
            st.success(outcome["headline"], icon=":material/verified:")
        else:
            st.warning(outcome["headline"], icon=":material/support_agent:")

        state_columns = st.columns(2)
        with state_columns[0].container(border=True, height="stretch"):
            st.caption("REPRESENTATIVE DECISION")
            st.subheader(decision_label)
            st.caption(f"Technical enum: `{decision}`")
        with state_columns[1].container(border=True, height="stretch"):
            st.caption("CASE STATUS")
            st.subheader(humanize(status))
            st.caption(f"Technical enum: `{status}`")

        if decision == "APPROVED":
            st.markdown("**Approved next step**")
            st.write(humanize(outcome["action"]))
            st.caption(f"Technical enum: `{outcome['action']}`")
            st.write(outcome["explanation"])
            if outcome.get("operational_next_step"):
                st.markdown("**Operational next step**")
                st.write(outcome["operational_next_step"])
            if outcome.get("evidence"):
                st.markdown("**Evidence referenced**")
                render_evidence_package(outcome["evidence"])
            if outcome.get("show_recovery"):
                render_recovery_evidence()
            if outcome.get("member_action_required"):
                detail_columns = st.columns(2)
                detail_columns[0].metric(
                    "Member action required", outcome["member_action_required"]
                )
                detail_columns[1].metric(
                    "Representative retains interaction ownership",
                    outcome["representative_ownership"],
                )
        else:
            st.markdown("**Specialist queue**")
            st.write(outcome["specialist_queue"])
            st.markdown("**Reason**")
            st.write(outcome["reason"])
            st.markdown("**Evidence package**")
            render_evidence_package(outcome["evidence"])

        render_case_continuity(decision)

    st.button(
        "Change representative decision",
        icon=":material/restart_alt:",
        on_click=reset_representative_decision,
        key=f"reset_decision_{scenario_id}",
    )


def render_representative_decision(
    case_state: dict[str, Any], scenario_id: str
) -> None:
    """Render the awaiting choice or the single persisted decision result."""

    st.subheader(":material/approval: Representative decision")
    decision = st.session_state.representative_decision
    if decision is None:
        st.write(
            "AI has completed the investigation and recommended the next step. "
            "A representative must approve the operational action or request "
            "specialist review."
        )
        with st.container(horizontal=True):
            st.button(
                "Approve recommended action",
                type="primary",
                icon=":material/check:",
                on_click=select_representative_decision,
                args=("APPROVED",),
                key=f"approve_{scenario_id}",
            )
            st.button(
                "Escalate for specialist review",
                type="primary",
                icon=":material/escalator_warning:",
                on_click=select_representative_decision,
                args=("ESCALATED",),
                key=f"escalate_{scenario_id}",
            )
    else:
        render_post_decision_result(case_state, scenario_id)


def render_resolution(
    case_state: dict[str, Any], scenario: dict[str, Any]
) -> None:
    st.header(":material/fact_check: Evidence-based resolution")
    st.success(
        "A consolidated recommendation is ready for the representative.",
        icon=":material/task_alt:",
    )

    status_columns = st.columns(3, vertical_alignment="center")
    with status_columns[0]:
        st.caption("Workflow status")
        st.badge(humanize(case_state["current_status"]), color="blue")
    with status_columns[1]:
        st.caption("Human approval required")
        st.badge(
            humanize(case_state["human_approval"]["required"]),
            color="orange" if case_state["human_approval"]["required"] else "green",
        )
    with status_columns[2]:
        st.caption("Member transfer required")
        st.badge(
            humanize(case_state["member_transfer_required"]),
            color="red" if case_state["member_transfer_required"] else "green",
        )

    decision_columns = st.columns(2)
    with decision_columns[0].container(border=True, height="stretch"):
        st.caption("Root cause")
        st.subheader(humanize(case_state["root_cause"]))
        st.write(case_state["root_cause_explanation"])
    with decision_columns[1].container(border=True, height="stretch"):
        st.caption("Recommended next action")
        st.subheader(humanize(case_state["recommended_action"]))
        st.write(case_state["recommended_action_summary"])

    with st.container(border=True):
        st.subheader(":material/source: Supporting evidence")
        for evidence in scenario["expected_evidence"]:
            st.markdown(f"- {evidence}")

    if case_state["human_approval"]["required"]:
        render_representative_decision(case_state, scenario["scenario_id"])


def render_operational_value(case_state: dict[str, Any]) -> None:
    st.header(":material/insights: Operational value")
    if st.session_state.representative_decision is not None:
        first_row = st.columns(3)
        first_row[0].metric("Member explanation captured", "Once")
        first_row[1].metric("Member transfer", "Avoided")
        first_row[2].metric("Repeated storytelling", "Avoided")
        second_row = st.columns(2)
        second_row[0].metric("Cross-system investigation", "Coordinated")
        second_row[1].metric("Human control", "Preserved")
        st.caption(
            "The representative decision changes only the prototype case state; no "
            "payer transaction is executed."
        )
        return

    unique_domain_agents = {
        agent
        for agent in case_state["agents_called"]
        if agent not in {"Intake Agent", "Resolution Agent"}
    }
    value_columns = st.columns(4)
    value_columns[0].metric("Member explanations", "1")
    value_columns[1].metric(
        "Member transfer", "Required" if case_state["member_transfer_required"] else "Avoided"
    )
    value_columns[2].metric("Investigation domains used", len(unique_domain_agents))
    value_columns[3].metric(
        "Alternate authorization path",
        "Used" if case_state["tool_errors"] else "Not needed",
    )
    st.caption(
        "The console supports faster evidence gathering, less manual navigation, "
        "consistent investigation steps, and better first-contact resolution support."
    )


def render_validation_evidence() -> None:
    st.header(":material/verified_user: Validation evidence")
    with st.container(border=True):
        columns = st.columns(3)
        columns[0].metric("Agentic scenarios", "4/4", border=True)
        columns[1].metric("Domain tool suite", "PASS", border=True)
        columns[2].metric("Demo data", "Synthetic", border=True)
        st.caption(
            "The four-scenario agentic evaluation and deterministic payer-domain tool "
            "suite were runtime-validated before this UI polish pass. This console uses "
            "those same repository fixtures in controlled playback mode."
        )


st.session_state.setdefault("case_state", None)
st.session_state.setdefault("investigated_scenario_id", None)
st.session_state.setdefault("representative_decision", None)
st.session_state.setdefault("post_decision_case_status", AWAITING_HUMAN_APPROVAL)
st.session_state.setdefault("channel", "Call")

datasets = get_demo_data()
scenarios = datasets["scenarios"]
scenario_names = {
    item["scenario_id"]: f"{item['scenario_id']} · {item['name']}" for item in scenarios
}

with st.container(horizontal=True, vertical_alignment="center"):
    st.title("OneCall AI — Healthcare resolution copilot")
    st.badge("Validated playback", color="blue", icon=":material/verified:")
st.subheader(
    "Resolve member issues through orchestrated payer-system checks in one guided interaction."
)
st.caption(
    "Synthetic healthcare payer prototype · The member explains the issue once; the "
    "system coordinates the investigation and returns evidence-backed next steps."
)

intake_column, architecture_column = st.columns([1, 1.35], gap="large")
with intake_column:
    st.subheader(":material/call: Interaction intake")
    with st.container(border=True):
        with st.container(horizontal=True, vertical_alignment="center"):
            st.markdown("**Validated demo scenario to replay**")
            st.badge("Start here", color="blue", icon=":material/play_circle:")
        selected_scenario_id = st.selectbox(
            "Validated demo scenario to replay",
            options=list(scenario_names),
            format_func=scenario_names.get,
            key="selected_scenario_id",
            label_visibility="collapsed",
            on_change=reset_case_for_scenario,
        )
        st.caption(
            "This is the primary demo control. Choose one of the four validated case "
            "paths before starting the investigation."
        )
        selected_scenario = next(
            item for item in scenarios if item["scenario_id"] == selected_scenario_id
        )
        intake = scenario_intake(selected_scenario, datasets)
        st.segmented_control(
            "Interaction channel",
            ["Call", "Chat"],
            key="channel",
            selection_mode="single",
        )
        with st.form("case_intake", border=False):
            field_columns = st.columns(2)
            field_columns[0].text_input(
                "Member ID",
                value=intake["member_id"],
                disabled=True,
                key=f"member_{selected_scenario_id}",
            )
            field_columns[1].text_input(
                "Service code",
                value=intake["service_code"],
                disabled=True,
                key=f"service_{selected_scenario_id}",
            )
            st.text_input(
                "Service date",
                value=intake["service_date"],
                disabled=True,
                key=f"date_{selected_scenario_id}",
            )
            member_inquiry = st.text_area(
                "Member inquiry / call note",
                value=selected_scenario["member_inquiry"],
                height=110,
                key=f"inquiry_{selected_scenario_id}",
            )
            submitted = st.form_submit_button(
                "Start resolution",
                type="primary",
                icon=":material/manage_search:",
                width="stretch",
            )
        st.caption(
            "Controlled playback uses validated synthetic fixtures; the intake note is "
            "retained in shared case context and does not alter payer facts."
        )

    if submitted:
        reset_representative_decision()
        if not member_inquiry.strip():
            st.warning("Enter a member inquiry before starting resolution.")
        else:
            try:
                resolved_case = simulate_scenario(selected_scenario_id, datasets)
                resolved_case["interaction"] = {
                    "channel": st.session_state.channel,
                    "member_inquiry": member_inquiry.strip(),
                }
                st.session_state.case_state = resolved_case
                st.session_state.investigated_scenario_id = selected_scenario_id
                apply_representative_state(resolved_case)
            except SimulationDataError as exc:
                st.error(f"The validated scenario could not be loaded: {exc}")

case_state = st.session_state.case_state
show_results = (
    case_state is not None
    and st.session_state.investigated_scenario_id == selected_scenario_id
)
active_case = case_state if show_results else None

if active_case:
    apply_representative_state(active_case)

with architecture_column:
    st.subheader(":material/hub: System architecture and request flow")
    st.caption(
        "One member explanation → shared case state → orchestrated system checks → "
        "evidence returned to the representative."
    )
    with st.container(border=True):
        render_architecture()

if active_case:
    st.success(
        "Playback complete · Review Case orchestration next.",
        icon=":material/south:",
    )
    st.header(":material/account_tree: Case orchestration")
    render_stage_progress(active_case)
    with st.status(
        "Orchestrated investigation complete",
        expanded=True,
        state="complete",
    ):
        for activity in active_case["investigation_trace"]:
            render_activity(activity)
        render_representative_orchestration_event(active_case)
    render_selected_path(active_case)
    render_resolution(active_case, selected_scenario)
    render_operational_value(active_case)
    render_validation_evidence()
    st.caption(
        "OneCall AI demonstrates decision support with synthetic data. It does not "
        "provide medical advice, determine clinical care, or perform payer-system writes."
    )
