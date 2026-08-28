import streamlit as st

from demo.simulator import load_datasets, simulate_scenario


st.set_page_config(page_title="OneCall AI", page_icon="\u2695\ufe0f", layout="wide")


@st.cache_data
def get_demo_data():
    return load_datasets()


def apply_approval_state(case_state, approval_status):
    if approval_status == "APPROVED":
        case_state["human_approval"]["status"] = "APPROVED"
        case_state["current_status"] = "READY_FOR_ACTION"
    elif approval_status == "ESCALATED":
        case_state["human_approval"]["status"] = "ESCALATED"
        case_state["current_status"] = "HUMAN_REVIEW_REQUIRED"


def render_activity(activity):
    decision = (
        f"  \n**Decision:** `{activity['decision']}`"
        if activity["decision"] is not None
        else ""
    )
    message = (
        f"**Step {activity['step']} · {activity['agent']} · "
        f"{activity['status']}**  \n{activity['summary']}{decision}"
    )
    if activity["status"] in {"SUCCESS", "RECOVERED"}:
        st.success(message, icon=":material/check_circle:")
    elif activity["status"] == "ERROR":
        st.error(message, icon=":material/error:")
    elif activity["status"] in {"RETRY", "HUMAN REVIEW"}:
        st.warning(message, icon=":material/warning:")
    else:
        st.info(message, icon=":material/arrow_forward:")


def display_value(label, value):
    st.caption(label)
    st.write(value)


def provider_summary(provider):
    if provider["status"] == "VALIDATED":
        return (
            f"{provider['organization_name']} · claim location "
            f"{provider['claim_location_network_status']} · authorization location "
            f"{provider['authorization_location_network_status']}"
        )
    if provider["status"] == "NOT_INVESTIGATED":
        return "Not required for resolution"
    return "Not applicable"


st.session_state.setdefault("case_state", None)
st.session_state.setdefault("investigated_scenario_id", None)
st.session_state.setdefault("approval_states", {})

datasets = get_demo_data()
scenarios = datasets["scenarios"]
members_by_id = {member["member_id"]: member for member in datasets["members"]}
scenario_names = {scenario["scenario_id"]: scenario["name"] for scenario in scenarios}

st.title("OneCall AI")
st.subheader("One member. One representative. One resolution.")
st.write("Reducing transfers, repeat calls, handle time, and servicing cost.")
st.caption("AI-assisted cross-domain investigation for healthcare payer member servicing.")
st.info(
    "Multi-agent healthcare payer servicing prototype using synthetic data only. "
    "No real PHI or member information is used.",
    icon=":material/health_and_safety:",
)

st.header("Member Service Case")
with st.container(border=True):
    selected_scenario_id = st.selectbox(
        "Select a demo member-service scenario",
        options=list(scenario_names),
        format_func=scenario_names.get,
        key="selected_scenario_id",
    )
    selected_scenario = next(
        scenario
        for scenario in scenarios
        if scenario["scenario_id"] == selected_scenario_id
    )
    selected_member = members_by_id[selected_scenario["member_id"]]

    case_columns = st.columns(2)
    with case_columns[0]:
        display_value("Member", selected_member["name"])
    with case_columns[1]:
        display_value("Plan", selected_member["plan_name"])
    display_value("Member inquiry", f'“{selected_scenario["member_inquiry"]}”')

    if st.button(
        "Investigate with OneCall AI",
        type="primary",
        icon=":material/manage_search:",
        key="investigate_case",
    ):
        case_state = simulate_scenario(selected_scenario_id, datasets)
        apply_approval_state(
            case_state,
            st.session_state.approval_states.get(selected_scenario_id),
        )
        st.session_state.case_state = case_state
        st.session_state.investigated_scenario_id = selected_scenario_id

case_state = st.session_state.case_state
show_results = (
    case_state is not None
    and st.session_state.investigated_scenario_id == selected_scenario_id
)

if show_results:
    apply_approval_state(
        case_state,
        st.session_state.approval_states.get(selected_scenario_id),
    )

    investigation_column, state_column = st.columns([1.7, 1])
    with investigation_column:
        st.header("Agent Investigation")
        with st.status(
            "Deterministic investigation complete",
            expanded=True,
            state="complete",
        ):
            for activity in case_state["investigation_trace"]:
                render_activity(activity)

    with state_column:
        st.header("Current Case State")
        with st.container(border=True):
            display_value("Case", case_state["case_id"])
            display_value("Member", case_state["member_name"])
            display_value("Eligibility", case_state["eligibility"]["status"])
            display_value("Benefit", case_state["benefit"]["status"])
            display_value(
                "Prior authorization required",
                (
                    "YES"
                    if case_state["benefit"].get("prior_authorization_required")
                    else "NO"
                ),
            )
            display_value("Claim status", case_state["claim"]["status"])
            display_value(
                "Authorization status", case_state["authorization"]["status"]
            )
            display_value("Provider / network", provider_summary(case_state["provider"]))
            display_value("Current Workflow State", case_state["current_status"])
            display_value("Root Cause", case_state["root_cause"])
            display_value("Next Best Action", case_state["recommended_action"])
            display_value(
                "Human Approval Status", case_state["human_approval"]["status"]
            )

    st.header("Resolution")
    st.success("ROOT CAUSE IDENTIFIED", icon=":material/task_alt:")
    with st.container(border=True):
        st.subheader(case_state["root_cause"].replace("_", " ").title())
        st.write(case_state["root_cause_explanation"])
        display_value(
            "Recommended Next Best Action", case_state["recommended_action"]
        )
        st.write(case_state["recommended_action_summary"])
        if case_state["member_transfer_required"]:
            st.warning("Member Transfer Required: YES", icon=":material/swap_horiz:")
        else:
            st.success("Member Transfer Required: NO", icon=":material/person_check:")

    if case_state["human_approval"]["required"]:
        st.subheader("Representative Approval Required")
        st.warning(
            "No payer record is modified. This is a synthetic demonstration.",
            icon=":material/front_hand:",
        )
        with st.container(horizontal=True):
            if st.button(
                "Approve Recommended Action",
                type="primary",
                icon=":material/check:",
                key=f"approve_{selected_scenario_id}",
            ):
                approval_states = dict(st.session_state.approval_states)
                approval_states[selected_scenario_id] = "APPROVED"
                st.session_state.approval_states = approval_states
                st.rerun()
            if st.button(
                "Escalate to Specialist",
                icon=":material/escalator_warning:",
                key=f"escalate_{selected_scenario_id}",
            ):
                approval_states = dict(st.session_state.approval_states)
                approval_states[selected_scenario_id] = "ESCALATED"
                st.session_state.approval_states = approval_states
                st.rerun()

        approval_status = case_state["human_approval"]["status"]
        if approval_status == "APPROVED":
            st.success(
                "Human Approval: APPROVED · Case Status: READY_FOR_ACTION",
                icon=":material/verified:",
            )
        elif approval_status == "ESCALATED":
            st.warning(
                "Human Approval: ESCALATED · Case Status: HUMAN_REVIEW_REQUIRED",
                icon=":material/support_agent:",
            )
