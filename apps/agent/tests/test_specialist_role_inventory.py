from app.services.specialist_role_inventory import build_specialist_role_inventory


def test_specialist_role_inventory_has_required_groups_and_no_duplicate_targets():
    inventory = build_specialist_role_inventory()
    summary = inventory["summary"]

    assert inventory["version"] == "specialist-role-inventory-v1"
    assert set(inventory["role_groups"]) == {
        "judgment_responsibility_agents",
        "observation_validation_agents",
        "presentation_guidance_agents",
    }
    assert summary["missing_groups"] == []
    assert summary["duplicate_target_roles"] == []
    assert summary["safe_metadata_only"] is True


def test_specialist_role_inventory_separates_observation_from_judgment_authority():
    inventory = build_specialist_role_inventory()

    observation_group = inventory["role_groups"]["observation_validation_agents"]
    assert "decide_fault_ratio" in observation_group["must_not_do"]
    assert "video_observation_agent" in observation_group["role_ids"]

    judgment_group = inventory["role_groups"]["judgment_responsibility_agents"]
    assert "traffic_accident_attorney" in judgment_group["role_ids"]
    assert "invent_law_or_precedent" in judgment_group["must_not_do"]


def test_presentation_roles_cannot_add_unverified_facts():
    inventory = build_specialist_role_inventory()

    presentation_group = inventory["role_groups"]["presentation_guidance_agents"]
    assert "presentation_policy_agent" in presentation_group["role_ids"]
    assert "add_unverified_legal_claim" in presentation_group["must_not_do"]
    assert any(rule["rule_id"] == "presentation_cannot_add_facts" for rule in inventory["boundary_rules"])
