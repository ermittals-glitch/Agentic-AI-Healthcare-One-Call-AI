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


def apply_approval_state(case_state: dict[str, Any], approval_status: str | None) -> None:
    """Apply a UI-only representative decision without performing a payer write."""

    if approval_status == "APPROVED":
        case_state["human_approval"]["status"] = "APPROVED"
        case_state["current_status"] = "READY_FOR_ACTION"
    elif approval_status == "ESCALATED":
        case_state["human_approval"]["status"] = "ESCALATED"
        case_state["current_status"] = "HUMAN_REVIEW_REQUIRED"


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
        st.subheader(":material/approval: Representative decision")
        st.caption(
            "The prototype recommends; it does not modify a payer record. A human "
            "must approve or escalate the next step."
        )
        with st.container(horizontal=True):
            if st.button(
                "Approve recommended action",
                type="primary",
                icon=":material/check:",
                key=f"approve_{scenario['scenario_id']}",
            ):
                approvals = dict(st.session_state.approval_states)
                approvals[scenario["scenario_id"]] = "APPROVED"
                st.session_state.approval_states = approvals
                st.rerun()
            if st.button(
                "Escalate to specialist",
                icon=":material/escalator_warning:",
                key=f"escalate_{scenario['scenario_id']}",
            ):
                approvals = dict(st.session_state.approval_states)
                approvals[scenario["scenario_id"]] = "ESCALATED"
                st.session_state.approval_states = approvals
                st.rerun()

        approval_status = case_state["human_approval"]["status"]
        if approval_status == "APPROVED":
            st.success(
                "Representative approved · Case is ready for the downstream action.",
                icon=":material/verified:",
            )
        elif approval_status == "ESCALATED":
            st.warning(
                "Specialist review requested · Member context remains attached.",
                icon=":material/support_agent:",
            )


def render_operational_value(case_state: dict[str, Any]) -> None:
    st.header(":material/insights: Operational value")
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
st.session_state.setdefault("approval_states", {})
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
        if not member_inquiry.strip():
            st.warning("Enter a member inquiry before starting resolution.")
        else:
            try:
                resolved_case = simulate_scenario(selected_scenario_id, datasets)
                resolved_case["interaction"] = {
                    "channel": st.session_state.channel,
                    "member_inquiry": member_inquiry.strip(),
                }
                apply_approval_state(
                    resolved_case,
                    st.session_state.approval_states.get(selected_scenario_id),
                )
                st.session_state.case_state = resolved_case
                st.session_state.investigated_scenario_id = selected_scenario_id
            except SimulationDataError as exc:
                st.error(f"The validated scenario could not be loaded: {exc}")

case_state = st.session_state.case_state
show_results = (
    case_state is not None
    and st.session_state.investigated_scenario_id == selected_scenario_id
)
active_case = case_state if show_results else None

if active_case:
    apply_approval_state(
        active_case, st.session_state.approval_states.get(selected_scenario_id)
    )

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
    render_selected_path(active_case)
    render_resolution(active_case, selected_scenario)
    render_operational_value(active_case)
    render_validation_evidence()
    st.caption(
        "OneCall AI demonstrates decision support with synthetic data. It does not "
        "provide medical advice, determine clinical care, or perform payer-system writes."
    )
