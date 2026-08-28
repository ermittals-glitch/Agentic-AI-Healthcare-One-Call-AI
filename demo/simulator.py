"""Deterministic, data-driven simulation for the OneCall AI public demo."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"
DATASET_FILES = {
    "members": "members.json",
    "benefits": "benefits.json",
    "claims": "claims.json",
    "authorizations": "authorizations.json",
    "providers": "providers.json",
    "scenarios": "scenarios.json",
}
APPROVAL_REQUIRED_ACTIONS = {
    "CLAIM_RECONSIDERATION",
    "PROVIDER_INITIATE_AUTHORIZATION",
    "ELIGIBILITY_RECORD_REVIEW",
}
ACTION_SUMMARIES = {
    "CLAIM_RECONSIDERATION": (
        "Submit the claim evidence for representative-approved reconsideration."
    ),
    "PROVIDER_INITIATE_AUTHORIZATION": (
        "Ask the provider to initiate the required prior authorization process."
    ),
    "ELIGIBILITY_RECORD_REVIEW": (
        "Route the conflicting eligibility record for representative-approved review."
    ),
}


class SimulationDataError(ValueError):
    """Raised when the synthetic datasets cannot support a scenario contract."""


def load_datasets(data_dir: str | Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Load the six synthetic JSON datasets from disk with basic shape checks."""

    base_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    datasets: dict[str, list[dict[str, Any]]] = {}

    for dataset_name, filename in DATASET_FILES.items():
        path = base_dir / filename
        try:
            with path.open(encoding="utf-8") as source:
                records = json.load(source)
        except (OSError, json.JSONDecodeError) as exc:
            raise SimulationDataError(f"Unable to load {path}: {exc}") from exc

        if not isinstance(records, list) or not all(
            isinstance(record, dict) for record in records
        ):
            raise SimulationDataError(f"{path} must contain a JSON array of objects.")
        datasets[dataset_name] = records

    return datasets


def simulate_scenario(
    scenario_id: str,
    datasets: Mapping[str, list[dict[str, Any]]] | None = None,
) -> dict[str, Any]:
    """Run one frozen scenario and return its resolved shared case state."""

    source = datasets if datasets is not None else load_datasets()
    scenario = _require_one(source["scenarios"], "scenario_id", scenario_id)
    member = _require_one(source["members"], "member_id", scenario["member_id"])
    claim = _optional_record(source["claims"], "claim_id", scenario.get("claim_id"))
    benefit = _find_benefit(source["benefits"], member, claim)
    state = _initial_case_state(scenario, member)

    _record_activity(
        state,
        "Intake Agent",
        "SUCCESS",
        "Member inquiry captured and a synthetic servicing case was opened.",
    )

    if scenario_id == "SCN003":
        _simulate_eligibility_mismatch(state, scenario, member, benefit)
    else:
        if claim is None:
            raise SimulationDataError(f"Scenario {scenario_id} requires a claim record.")
        _simulate_claim_scenario(state, scenario, member, benefit, claim, source)

    _validate_contract(state, scenario)
    return state


def _simulate_claim_scenario(
    state: dict[str, Any],
    scenario: dict[str, Any],
    member: dict[str, Any],
    benefit: dict[str, Any],
    claim: dict[str, Any],
    datasets: Mapping[str, list[dict[str, Any]]],
) -> None:
    _record_activity(
        state,
        "Orchestrator",
        "DECISION",
        "Verify coverage on the claim's date of service.",
        "CHECK_ELIGIBILITY",
    )
    coverage_active = _coverage_active_on(member, claim["service_date"])
    state["eligibility"] = {
        "status": member["coverage_status"],
        "active_on_service_date": coverage_active,
        "coverage_effective_date": member["coverage_effective_date"],
        "coverage_termination_date": member["coverage_termination_date"],
        "enrollment_status": member["enrollment_status"],
    }
    _record_activity(
        state,
        "Eligibility Agent",
        "SUCCESS",
        f"Coverage is {member['coverage_status']} on {claim['service_date']}.",
    )

    _record_activity(
        state,
        "Orchestrator",
        "DECISION",
        "Confirm the service benefit and authorization requirement.",
        "CHECK_BENEFITS",
    )
    state["benefit"] = {
        "status": "COVERED" if benefit["covered"] else "NOT_COVERED",
        "benefit_id": benefit["benefit_id"],
        "service_code": benefit["service_code"],
        "service_name": benefit["service_name"],
        "covered": benefit["covered"],
        "prior_authorization_required": benefit["prior_authorization_required"],
        "network_requirement": benefit["network_requirement"],
    }
    authorization_requirement = (
        "Prior authorization is required."
        if benefit["prior_authorization_required"]
        else "Prior authorization is not required."
    )
    _record_activity(
        state,
        "Benefits Agent",
        "SUCCESS",
        f"{benefit['service_name']} is covered. {authorization_requirement}",
    )

    _record_activity(
        state,
        "Orchestrator",
        "DECISION",
        "Review the claim outcome and denial evidence.",
        "REVIEW_CLAIM",
    )
    state["claim"] = {
        "status": claim["status"],
        "claim_id": claim["claim_id"],
        "service_date": claim["service_date"],
        "service_code": claim["service"]["service_code"],
        "service_name": claim["service"]["service_name"],
        "denial_reason": claim["denial_reason"],
        "authorization_reference": claim["authorization_reference"],
        "provider_id": claim["provider_id"],
        "provider_location_id": claim["provider_location_id"],
    }
    _record_activity(
        state,
        "Claims Agent",
        "SUCCESS",
        (
            f"Claim {claim['claim_id']} is {claim['status']} with reason "
            f"{claim['denial_reason']}."
        ),
    )

    _record_activity(
        state,
        "Orchestrator",
        "DECISION",
        "Authorization evidence is required to explain the denial.",
        "CHECK_AUTHORIZATION",
    )

    if scenario["scenario_id"] == "SCN004":
        authorizations = _simulate_authorization_recovery(
            state, scenario, claim, datasets["authorizations"]
        )
    else:
        authorizations = _matching_authorizations(datasets["authorizations"], claim)

    authorization = authorizations[0] if authorizations else None
    if authorization is None:
        state["authorization"] = {
            "status": "NOT_FOUND",
            "authorization_id": None,
            "lookup_method": "MEMBER_SERVICE_DATE",
        }
        _record_activity(
            state,
            "Authorization Agent",
            "SUCCESS",
            "No matching authorization exists for the member, service, and date.",
        )
    elif scenario["scenario_id"] != "SCN004":
        state["authorization"] = _authorization_state(
            authorization, lookup_method="MEMBER_SERVICE_DATE"
        )
        _record_activity(
            state,
            "Authorization Agent",
            "SUCCESS",
            (
                f"Authorization {authorization['authorization_id']} was found with "
                f"status {authorization['status']}."
            ),
        )

    if scenario["scenario_id"] == "SCN001":
        if authorization is None:
            raise SimulationDataError("Scenario SCN001 requires an authorization.")
        provider = _build_provider_state(datasets["providers"], claim, authorization)
        state["provider"] = provider
        _record_activity(
            state,
            "Orchestrator",
            "DECISION",
            "Validate the provider organization, locations, and network status.",
            "VALIDATE_PROVIDER_LOCATION",
        )
        _record_activity(
            state,
            "Provider Agent",
            "SUCCESS",
            (
                f"Both locations belong to {provider['organization_name']} and are "
                f"in network; the claim used {provider['claim_location_name']} while "
                f"the authorization used {provider['authorization_location_name']}."
            ),
        )
    elif authorization is not None:
        state["provider"] = _build_provider_state(
            datasets["providers"], claim, authorization
        )
    else:
        state["provider"] = {
            "status": "NOT_INVESTIGATED",
            "reason": "Provider validation is not required to resolve this case.",
        }

    root_cause, action, explanation = _resolve_claim_case(
        scenario["scenario_id"], state, claim, authorization
    )
    _complete_case(state, scenario, root_cause, action, explanation)


def _simulate_authorization_recovery(
    state: dict[str, Any],
    scenario: dict[str, Any],
    claim: dict[str, Any],
    authorizations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not scenario.get("primary_lookup_failure"):
        raise SimulationDataError("SCN004 must configure primary lookup failure.")

    _record_tool_error(
        state,
        "PRIMARY_AUTHORIZATION_LOOKUP",
        "Primary authorization lookup unavailable.",
    )
    _record_activity(
        state,
        "Authorization Agent",
        "ERROR",
        "Primary authorization lookup unavailable.",
    )

    _record_activity(
        state,
        "Orchestrator",
        "RETRY",
        "Retry the primary authorization lookup once.",
        "RETRY_AUTHORIZATION_LOOKUP",
    )
    if not scenario.get("retry_failure"):
        raise SimulationDataError("SCN004 must configure retry failure.")

    _record_tool_error(
        state,
        "RETRY_AUTHORIZATION_LOOKUP",
        "Authorization lookup retry failed.",
    )
    _record_activity(
        state,
        "Authorization Agent",
        "ERROR",
        "Authorization lookup retry failed.",
    )

    _record_activity(
        state,
        "Orchestrator",
        "DECISION",
        "Use alternate lookup with member, service, and date.",
        "ALTERNATE_LOOKUP",
    )
    matches = _matching_authorizations(authorizations, claim)
    if not scenario.get("alternate_lookup_success") or not matches:
        raise SimulationDataError("SCN004 alternate authorization lookup did not recover.")

    authorization = matches[0]
    state["authorization"] = _authorization_state(
        authorization, lookup_method="ALTERNATE_MEMBER_SERVICE_DATE"
    )
    _record_activity(
        state,
        "Authorization Agent",
        "RECOVERED",
        (
            f"Authorization {authorization['authorization_id']} was located using "
            "alternate member, service, and date lookup."
        ),
        "SUCCESS",
    )
    return matches


def _simulate_eligibility_mismatch(
    state: dict[str, Any],
    scenario: dict[str, Any],
    member: dict[str, Any],
    benefit: dict[str, Any],
) -> None:
    _record_activity(
        state,
        "Orchestrator",
        "DECISION",
        "Compare servicing eligibility with enrollment evidence.",
        "CHECK_ELIGIBILITY_AND_ENROLLMENT",
    )
    state["eligibility"] = {
        "status": member["coverage_status"],
        "active_on_service_date": None,
        "coverage_effective_date": member["coverage_effective_date"],
        "coverage_termination_date": member["coverage_termination_date"],
        "enrollment_status": member["enrollment_status"],
        "enrollment_effective_date": member["enrollment_effective_date"],
        "eligibility_last_synced_date": member["eligibility_last_synced_date"],
    }
    _record_activity(
        state,
        "Eligibility Agent",
        "SUCCESS",
        (
            f"Servicing coverage shows {member['coverage_status']}, while enrollment "
            f"shows {member['enrollment_status']}."
        ),
    )

    _record_activity(
        state,
        "Orchestrator",
        "DECISION",
        "Investigate the enrollment timeline and plan benefit record.",
        "CHECK_ENROLLMENT_AND_BENEFITS",
    )
    state["benefit"] = {
        "status": "COVERED" if benefit["covered"] else "NOT_COVERED",
        "benefit_id": benefit["benefit_id"],
        "service_code": benefit["service_code"],
        "service_name": benefit["service_name"],
        "covered": benefit["covered"],
        "prior_authorization_required": benefit["prior_authorization_required"],
        "network_requirement": benefit["network_requirement"],
    }
    state["claim"] = {"status": "NOT_APPLICABLE"}
    state["authorization"] = {"status": "NOT_APPLICABLE"}
    state["provider"] = {"status": "NOT_APPLICABLE"}
    _record_activity(
        state,
        "Enrollment / Benefits Agent",
        "SUCCESS",
        (
            f"Enrollment became active on {member['enrollment_effective_date']}; the "
            f"eligibility view was last synchronized on "
            f"{member['eligibility_last_synced_date']} and has no termination date."
        ),
    )

    stale_eligibility = date.fromisoformat(
        member["eligibility_last_synced_date"]
    ) < date.fromisoformat(member["enrollment_effective_date"])
    mismatch = (
        member["enrollment_status"] == "ACTIVE"
        and member["coverage_status"] != "ACTIVE"
        and member["coverage_termination_date"] is None
        and stale_eligibility
    )
    if not mismatch:
        raise SimulationDataError("SCN003 lacks an eligibility/enrollment mismatch.")

    explanation = (
        f"Enrollment for {member['name']} is active from "
        f"{member['enrollment_effective_date']}, but the servicing eligibility view "
        f"still reports {member['coverage_status']} and was last synchronized on "
        f"{member['eligibility_last_synced_date']}."
    )
    _complete_case(
        state,
        scenario,
        "ELIGIBILITY_ENROLLMENT_MISMATCH",
        "ELIGIBILITY_RECORD_REVIEW",
        explanation,
    )


def _resolve_claim_case(
    scenario_id: str,
    state: dict[str, Any],
    claim: dict[str, Any],
    authorization: dict[str, Any] | None,
) -> tuple[str, str, str]:
    common_conditions = (
        state["eligibility"]["active_on_service_date"] is True
        and state["benefit"]["covered"] is True
        and state["benefit"]["prior_authorization_required"] is True
        and claim["status"] == "DENIED"
        and claim["denial_reason"] == "AUTHORIZATION_NOT_FOUND"
    )
    if not common_conditions:
        raise SimulationDataError(f"{scenario_id} lacks required claim evidence.")

    if scenario_id == "SCN001":
        provider = state["provider"]
        mismatch = (
            authorization is not None
            and authorization["status"] == "APPROVED"
            and provider["same_provider_organization"] is True
            and provider["location_mismatch"] is True
            and provider["claim_location_network_status"] == "IN_NETWORK"
            and provider["authorization_location_network_status"] == "IN_NETWORK"
        )
        if not mismatch:
            raise SimulationDataError("SCN001 lacks a provider-location mismatch.")
        explanation = (
            f"Claim {claim['claim_id']} used {provider['claim_location_name']}, while "
            f"approved authorization {authorization['authorization_id']} used "
            f"{provider['authorization_location_name']}. Both are in-network locations "
            f"of {provider['organization_name']}."
        )
        return (
            "AUTHORIZATION_CLAIM_LOCATION_MISMATCH",
            "CLAIM_RECONSIDERATION",
            explanation,
        )

    if scenario_id == "SCN002":
        if authorization is not None:
            raise SimulationDataError("SCN002 unexpectedly found an authorization.")
        explanation = (
            f"Claim {claim['claim_id']} requires prior authorization, but no approved "
            "authorization exists for this member, service, and date."
        )
        return (
            "PRIOR_AUTHORIZATION_MISSING",
            "PROVIDER_INITIATE_AUTHORIZATION",
            explanation,
        )

    if scenario_id == "SCN004":
        recovered = any(
            activity["status"] == "RECOVERED"
            for activity in state["investigation_trace"]
        )
        link_failure = (
            recovered
            and authorization is not None
            and authorization["status"] == "APPROVED"
            and claim["authorization_reference"] is None
        )
        if not link_failure:
            raise SimulationDataError("SCN004 lacks recoverable claim-link evidence.")
        explanation = (
            f"The primary lookup and retry failed, but alternate lookup found approved "
            f"authorization {authorization['authorization_id']}. Claim "
            f"{claim['claim_id']} did not contain an authorization reference."
        )
        return (
            "AUTHORIZATION_CLAIM_LINK_FAILURE",
            "CLAIM_RECONSIDERATION",
            explanation,
        )

    raise SimulationDataError(f"Unsupported claim scenario: {scenario_id}")


def _complete_case(
    state: dict[str, Any],
    scenario: dict[str, Any],
    root_cause: str,
    action: str,
    explanation: str,
) -> None:
    state["root_cause"] = root_cause
    state["root_cause_explanation"] = explanation
    state["recommended_action"] = action
    state["recommended_action_summary"] = ACTION_SUMMARIES[action]
    state["member_transfer_required"] = bool(
        scenario["expected_member_transfer_required"]
    )
    approval_required = action in APPROVAL_REQUIRED_ACTIONS
    state["human_approval"] = {
        "required": approval_required,
        "status": "PENDING" if approval_required else "NOT_REQUIRED",
        "external_write_performed": False,
    }
    state["current_status"] = (
        "AWAITING_REPRESENTATIVE_APPROVAL" if approval_required else "RESOLVED"
    )
    _record_activity(
        state,
        "Orchestrator",
        "DECISION",
        f"Root cause identified: {root_cause}.",
        action,
    )
    _record_activity(
        state,
        "Resolution Agent",
        "SUCCESS",
        explanation,
        action,
    )
    if approval_required:
        _record_activity(
            state,
            "Orchestrator",
            "HUMAN REVIEW",
            "Representative approval is required before any recommended action.",
            "REQUEST_REPRESENTATIVE_APPROVAL",
        )


def _initial_case_state(
    scenario: dict[str, Any], member: dict[str, Any]
) -> dict[str, Any]:
    return {
        "case_id": f"CASE-{scenario['scenario_id']}-{member['member_id']}",
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["name"],
        "member_id": member["member_id"],
        "member_name": member["name"],
        "plan_id": member["plan_id"],
        "plan_name": member["plan_name"],
        "member_inquiry": scenario["member_inquiry"],
        "current_status": "INVESTIGATING",
        "eligibility": {"status": "UNKNOWN"},
        "benefit": {"status": "UNKNOWN"},
        "claim": {"status": "UNKNOWN"},
        "authorization": {"status": "UNKNOWN"},
        "provider": {"status": "UNKNOWN"},
        "agents_called": [],
        "investigation_trace": [],
        "root_cause": "UNRESOLVED",
        "root_cause_explanation": "",
        "recommended_action": "UNRESOLVED",
        "recommended_action_summary": "",
        "member_transfer_required": "UNKNOWN",
        "human_approval": {
            "required": "UNKNOWN",
            "status": "NOT_REQUESTED",
            "external_write_performed": False,
        },
        "tool_errors": [],
    }


def _record_activity(
    state: dict[str, Any],
    agent: str,
    status: str,
    summary: str,
    decision: str | None = None,
) -> None:
    state["investigation_trace"].append(
        {
            "step": len(state["investigation_trace"]) + 1,
            "agent": agent,
            "status": status,
            "summary": summary,
            "decision": decision,
        }
    )
    if agent.endswith("Agent") and agent not in state["agents_called"]:
        state["agents_called"].append(agent)


def _record_tool_error(
    state: dict[str, Any], operation: str, message: str
) -> None:
    state["tool_errors"].append(
        {
            "agent": "Authorization Agent",
            "operation": operation,
            "error": message,
            "recoverable": True,
        }
    )


def _coverage_active_on(member: dict[str, Any], service_date: str) -> bool:
    date_of_service = date.fromisoformat(service_date)
    effective = date.fromisoformat(member["coverage_effective_date"])
    termination_value = member.get("coverage_termination_date")
    termination = date.fromisoformat(termination_value) if termination_value else None
    return (
        member["coverage_status"] == "ACTIVE"
        and effective <= date_of_service
        and (termination is None or date_of_service <= termination)
    )


def _find_benefit(
    benefits: list[dict[str, Any]],
    member: dict[str, Any],
    claim: dict[str, Any] | None,
) -> dict[str, Any]:
    matches = [benefit for benefit in benefits if benefit["plan_id"] == member["plan_id"]]
    if claim is not None:
        service_code = claim["service"]["service_code"]
        matches = [benefit for benefit in matches if benefit["service_code"] == service_code]
    if len(matches) != 1:
        raise SimulationDataError(
            f"Expected one benefit for member {member['member_id']}; found {len(matches)}."
        )
    return matches[0]


def _matching_authorizations(
    authorizations: list[dict[str, Any]], claim: dict[str, Any]
) -> list[dict[str, Any]]:
    service_date = date.fromisoformat(claim["service_date"])
    return [
        authorization
        for authorization in authorizations
        if authorization["member_id"] == claim["member_id"]
        and authorization["service"]["service_code"]
        == claim["service"]["service_code"]
        and authorization["status"] == "APPROVED"
        and date.fromisoformat(authorization["effective_start_date"])
        <= service_date
        <= date.fromisoformat(authorization["effective_end_date"])
    ]


def _authorization_state(
    authorization: dict[str, Any], lookup_method: str
) -> dict[str, Any]:
    return {
        "status": authorization["status"],
        "authorization_id": authorization["authorization_id"],
        "effective_start_date": authorization["effective_start_date"],
        "effective_end_date": authorization["effective_end_date"],
        "provider_id": authorization["provider_id"],
        "provider_location_id": authorization["provider_location_id"],
        "lookup_method": lookup_method,
    }


def _build_provider_state(
    providers: list[dict[str, Any]],
    claim: dict[str, Any],
    authorization: dict[str, Any],
) -> dict[str, Any]:
    claim_provider = _require_one(providers, "provider_id", claim["provider_id"])
    authorization_provider = _require_one(
        providers, "provider_id", authorization["provider_id"]
    )
    claim_location = _require_one(
        claim_provider["locations"],
        "provider_location_id",
        claim["provider_location_id"],
    )
    authorization_location = _require_one(
        authorization_provider["locations"],
        "provider_location_id",
        authorization["provider_location_id"],
    )
    same_provider = claim_provider["provider_id"] == authorization_provider["provider_id"]
    return {
        "status": "VALIDATED",
        "organization_name": claim_provider["organization_name"],
        "same_provider_organization": same_provider,
        "location_mismatch": (
            claim_location["provider_location_id"]
            != authorization_location["provider_location_id"]
        ),
        "claim_location_id": claim_location["provider_location_id"],
        "claim_location_name": claim_location["location_name"],
        "claim_location_network_status": claim_location["network_status"],
        "authorization_location_id": authorization_location["provider_location_id"],
        "authorization_location_name": authorization_location["location_name"],
        "authorization_location_network_status": authorization_location["network_status"],
    }


def _require_one(
    records: list[dict[str, Any]], field: str, value: Any
) -> dict[str, Any]:
    matches = [record for record in records if record.get(field) == value]
    if len(matches) != 1:
        raise SimulationDataError(
            f"Expected one record where {field}={value!r}; found {len(matches)}."
        )
    return matches[0]


def _optional_record(
    records: list[dict[str, Any]], field: str, value: Any
) -> dict[str, Any] | None:
    if value is None:
        return None
    return _require_one(records, field, value)


def _validate_contract(state: dict[str, Any], scenario: dict[str, Any]) -> None:
    comparisons = {
        "root cause": (state["root_cause"], scenario["expected_root_cause"]),
        "recommended action": (
            state["recommended_action"],
            scenario["expected_recommended_action"],
        ),
        "member transfer requirement": (
            state["member_transfer_required"],
            scenario["expected_member_transfer_required"],
        ),
    }
    for label, (actual, expected) in comparisons.items():
        if actual != expected:
            raise SimulationDataError(
                f"{scenario['scenario_id']} {label} was {actual!r}; expected {expected!r}."
            )
