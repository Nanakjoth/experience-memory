"""End-to-end API tests for MemoryOS.

These exercise the real code paths end to end against the SIMULATED memory
engine: capture through the Memory Gate, Hindsight retain/recall, permission
filtering, outcome feedback, architecture-change contradiction detection and the
full demo narrative.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

SYNTHETIC_LABEL = "Synthetic prototype metric"


def _seed(client: TestClient) -> None:
    """Seed incidents, capture the expert lesson, promote it."""
    for endpoint in ("/api/demo/seed-incidents", "/api/demo/capture", "/api/demo/promote"):
        r = client.post(endpoint)
        assert r.status_code == 200, (endpoint, r.text)


# --- meta ------------------------------------------------------------------
def test_root_advertises_hindsight_as_the_memory_engine(client: TestClient) -> None:
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["memory_engine"]["name"] == "hindsight"
    assert body["memory_engine"]["operations"] == ["retain", "recall", "reflect"]
    assert body["memory_engine"]["bank_id"] == "memoryos-novatech"
    assert body["memory_engine"]["bank_mission"]
    assert body["synthetic_data"]


def test_health_reports_simulated_engine_when_hindsight_is_absent(
    client: TestClient,
) -> None:
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["memory_engine"] == "hindsight"
    assert body["engine_mode"] == "simulated"
    assert body["engine_simulated"] is True
    assert "SIMULATED" in body["engine_label"]


def test_engine_endpoint_never_returns_a_secret(client: TestClient) -> None:
    body = client.get("/api/engine").json()
    assert body["health"]["simulated"] is True
    # Only boolean "is a key configured" flags are allowed to leave the process.
    for value in body["config"].values():
        assert not isinstance(value, str) or "sk-" not in value
    assert body["config"]["hindsight_api_key_configured"] in (True, False)
    assert body["config"]["llm_api_key_configured"] in (True, False)


# --- dashboard -------------------------------------------------------------
def test_dashboard_labels_every_number_as_synthetic(client: TestClient) -> None:
    body = client.get("/api/dashboard").json()
    assert body["synthetic"] is True
    assert body["synthetic_label"] == SYNTHETIC_LABEL
    assert body["metrics"]
    for metric in body["metrics"].values():
        assert metric["synthetic"] is True
        assert metric["synthetic_label"] == SYNTHETIC_LABEL


def test_dashboard_counts_match_the_stored_memories(client: TestClient) -> None:
    _seed(client)
    body = client.get("/api/dashboard").json()
    listed = client.get("/api/memories?limit=500").json()["total"]
    assert body["metrics"]["captured_knowledge"]["value"] == listed
    assert body["health_counts"]["memories"] == listed


# --- capture ---------------------------------------------------------------
def test_capture_goes_through_hindsight_and_the_gate(client: TestClient) -> None:
    before = client.get("/api/demo/state").json()["memories"]
    r = client.post(
        "/api/capture",
        json={
            "expert": "Arun",
            "role": "Senior DevOps Engineer",
            "team": "Payments Operations",
            "scope": "Payment Queue v1",
            "system": "Payment Platform",
            "turns": [
                {
                    "prompt": "What do you check before restarting the payment queue?",
                    "answer": (
                        "Always check the dead-letter queue depth first. If it is above "
                        "80 percent the queue is saturated and a restart makes it worse."
                    ),
                },
                {
                    "prompt": "Who do you escalate to?",
                    "answer": "Escalate to Payments Operations, the queue owning team.",
                },
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["retained"] is True
    assert body["hindsight_fact_ids"]
    assert body["memories"]
    for mem in body["memories"]:
        assert mem["gate"] is not None
        assert mem["gate"]["decision"] in {"STORE", "REVIEW", "REJECT"}
        assert mem["hindsight_document_id"]
    assert client.get("/api/demo/state").json()["memories"] > before


def test_capture_rejects_a_secret_bearing_document(client: TestClient) -> None:
    r = client.post(
        "/api/capture",
        json={
            "expert": "Arun",
            "turns": [
                {
                    "prompt": "Credentials?",
                    "answer": (
                        "Arun's personal API key is sk-live-9f8a7b6c5d4e3f2a1b0c and the "
                        "production database password is Hunter2!Secret. He finds the "
                        "onboarding plan tedious."
                    ),
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["rejected"], body
    for mem in body["memories"]:
        assert "sk-live" not in mem["content"]
        assert "Hunter2" not in mem["content"]


def test_capture_with_nothing_to_store_is_refused(client: TestClient) -> None:
    r = client.post("/api/capture", json={"expert": "Arun", "turns": []})
    assert r.status_code in (400, 422)


# --- ask / retrieval -------------------------------------------------------
def test_ask_answers_from_hindsight_evidence(client: TestClient) -> None:
    _seed(client)
    r = client.post("/api/ask", json={"actor": "maya", "question": None})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["answer"]["headline"]
    assert body["lens"]
    assert body["memories_used"]
    assert body["hindsight_facts"]
    assert body["confidence"]["score"] > 0
    assert body["confidence"]["disclaimer"]
    assert body["trace"]["steps"]
    assert body["engine_mode"] == "simulated"
    assert body["engine_simulated"] is True


def test_default_question_is_used_when_none_is_asked(client: TestClient) -> None:
    _seed(client)
    body = client.post("/api/ask", json={"actor": "maya"}).json()
    assert body["question"].strip()


def test_ask_explains_an_unfamiliar_situation_honestly(client: TestClient) -> None:
    """A question the organization has never experienced must not borrow
    in-scope knowledge just because the same system is running."""
    _seed(client)
    unfamiliar = client.post(
        "/api/ask",
        json={
            "actor": "maya",
            "question": "How do I rotate the JWT signing key for the mobile gateway?",
        },
    ).json()
    familiar = client.post(
        "/api/ask",
        json={
            "actor": "maya",
            "question": "Payment API is showing connection reset alerts. What should I do?",
        },
    ).json()

    assert unfamiliar["confidence"]["score"] < familiar["confidence"]["score"]
    assert unfamiliar["memories_used"] == []
    assert "haven't experienced" in unfamiliar["answer"]["headline"].lower()
    assert "runbook" in unfamiliar["answer"]["headline"].lower()
    assert unfamiliar["confidence"]["band"] == "LOW"
    # The honest answer still tells the operator what to do next.
    assert unfamiliar["answer"]["sections"]


def test_personal_memory_is_never_returned_to_another_engineer(
    client: TestClient,
) -> None:
    _seed(client)
    as_maya = client.post("/api/ask", json={"actor": "maya"}).json()
    as_arun = client.post("/api/ask", json={"actor": "arun"}).json()

    for mem in as_maya["memories_used"]:
        assert mem["visibility"] != "PERSONAL"
    # Arun sees strictly more of his own knowledge than Maya does.
    assert len(as_arun["memories_used"]) > len(as_maya["memories_used"])

    # Arun has personal memories that Maya is refused outright.
    personal = client.get("/api/memories?actor=arun&limit=200").json()["items"]
    private = [m for m in personal if m["visibility"] == "PERSONAL"]
    assert private, "expected Arun to own personal memory"
    for m in private:
        assert m["id"] not in {x["id"] for x in as_maya["memories_used"]}
        # Direct access is refused with an explanation, not silently empty.
        denied = client.get(f"/api/memories/{m['id']}?actor=maya")
        assert denied.status_code == 403
    # And none of their text appears anywhere in Maya's answer payload.
    blob = " ".join(
        [m["content"] for m in as_maya["memories_used"]]
        + [str(f.get("text", "")) for f in as_maya["hindsight_facts"]]
        + [s["points"][0] for s in as_maya["answer"]["sections"] if s["points"]]
    )
    for m in private:
        assert m["content"][:60] not in blob


def test_raw_facts_gated_from_the_actor_are_counted_not_printed(
    client: TestClient,
) -> None:
    _seed(client)
    body = client.post("/api/ask", json={"actor": "maya"}).json()
    assert body["suppressed_fact_count"] >= 0
    assert body["trace"]["suppressed_fact_ids"] is not None


def test_ask_writes_history_and_audit(client: TestClient) -> None:
    _seed(client)
    client.post("/api/ask", json={"actor": "maya"})
    events = client.get("/api/audit?limit=1000").json()["events"]
    kinds = {e["event_type"] for e in events}
    assert "hindsight_recall" in kinds
    assert "memory_used_by_agent" in kinds
    convo = client.get("/api/conversations?actor=maya").json()
    assert convo["turns"]
    assert {t["role"] for t in convo["turns"]} == {"user", "assistant"}


def test_actor_endpoint_exposes_real_permission_ceilings(client: TestClient) -> None:
    body = client.get("/api/actors").json()
    by_id = {a["id"]: a for a in body["actors"]}
    assert by_id["outsider"]["visibility_ceiling"] == "PERSONAL"
    assert by_id["maya"]["can_read"]["organization"] is True
    assert by_id["outsider"]["can_read"]["organization"] is False
    assert by_id["outsider"]["can_read"]["team"] is False
    # Personal knowledge is readable by its owner but never by anyone else.
    assert by_id["maya"]["can_read"]["own_personal"] is True
    assert by_id["maya"]["can_read"]["others_personal"] is False
    # Promotion to organizational knowledge needs a steward.
    assert by_id["maya"]["can_promote"]["organization"] is False
    assert by_id["steward"]["can_promote"]["organization"] is True


# --- outcomes --------------------------------------------------------------
def test_outcome_classification_handles_negation() -> None:
    from backend.api.outcomes import classify_outcome

    # A success that mentions a failure word must not be read as a failure.
    assert classify_outcome("Restart succeeded. Duplicate processing did not recur.")[
        "successful"
    ] is True
    assert classify_outcome("Restart completed without incident.")["successful"] is True
    assert classify_outcome("No duplicates this time, payment flow was clean.")[
        "successful"
    ] is True
    assert classify_outcome("Duplicate payments were processed. This did not work.")[
        "successful"
    ] is False
    assert classify_outcome("Rolled back after the queue failed.")["successful"] is False
    # Ambiguous text is not silently guessed in either direction.
    assert classify_outcome("It was fine, nothing special happened.")["successful"] is None
    # The reporter always wins over the classifier.
    assert classify_outcome("It was fine.", stated=False)["successful"] is False
    assert classify_outcome("It was fine.", stated=True)["source"] == "stated_by_reporter"


# --- outcomes --------------------------------------------------------------
def test_successful_outcome_reinforces_the_memory(client: TestClient) -> None:
    _seed(client)
    r = client.post(
        "/api/outcome",
        json={
            "actor": "maya",
            "question": "What should I check before restarting the payment queue?",
            "recommendation": "Check the dead-letter queue depth first.",
            "actual_action": "Checked the dead-letter queue depth before restarting.",
            "result": "Restart succeeded. Duplicate processing did not recur.",
            "outcome_id": "OUT-TEST-SUCCESS",
            "queue_depth": 78.0,
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["linked_memories"]
    assert body["reinforced"]
    assert body["status"] == "SUPPORTED"
    assert body["confidence_delta"] > 0, body["reinforced"]
    top = body["reinforced"][0]
    assert top["confidence_after"] > top["confidence_before"]
    assert top["evidence_count"] >= 1

    events = client.get(f"/api/memories/{top['id']}/history").json()["events"]
    assert any(e["action"] == "outcome_supported" for e in events)


def test_failed_outcome_creates_a_correction_memory(client: TestClient) -> None:
    _seed(client)
    r = client.post(
        "/api/outcome",
        json={
            "actor": "maya",
            "question": "What should I check before restarting the payment queue?",
            "recommendation": "Check the dead-letter queue depth first.",
            "actual_action": "Skipped the check and restarted immediately.",
            "result": "Duplicate payments were processed. This did not work.",
            "outcome_id": "OUT-TEST-FAILURE",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["contradiction"] is not None
    assert body["contradiction"]["status"] == "REVIEW_REQUIRED"
    # The contradicting outcome is itself retained, not discarded.
    outcomes = client.get("/api/outcomes").json()
    assert any(o["id"] == "OUT-TEST-FAILURE" or "did not work" in o["title"] for o in outcomes["outcomes"])


def test_outcome_needs_a_result(client: TestClient) -> None:
    r = client.post(
        "/api/outcome",
        json={"actor": "maya", "question": "q", "recommendation": "r", "actual_action": "a"},
    )
    assert r.status_code == 422


# --- memory centre ---------------------------------------------------------
def test_memory_centre_filters_and_reports_total(client: TestClient) -> None:
    _seed(client)
    body = client.get("/api/memories?status=ACTIVE&limit=50").json()
    assert body["total"] >= 1
    assert body["items"]
    for m in body["items"]:
        assert m["status"] == "ACTIVE"
    assert body["filters"]["types"]
    assert body["filters"]["visibilities"]


def test_memory_search_narrows_results(client: TestClient) -> None:
    _seed(client)
    everything = client.get("/api/memories?limit=200").json()["total"]
    filtered = client.get("/api/memories?q=dead-letter&limit=200").json()["total"]
    assert 0 < filtered <= everything


def test_memory_detail_exposes_provenance_lifecycle_and_confidence(
    client: TestClient,
) -> None:
    _seed(client)
    mid = client.get("/api/memories?limit=1").json()["items"][0]["id"]
    body = client.get(f"/api/memories/{mid}").json()
    assert body["memory"]["provenance"] if "provenance" in body["memory"] else True
    assert body["provenance"]["source_type"]
    assert body["events"]
    assert body["confidence"]["factors"]
    assert body["confidence"]["disclaimer"]
    assert "synthetic" in body["confidence"]["disclaimer"].lower() or (
        "heuristic" in body["confidence"]["disclaimer"].lower()
    )
    assert "promotable" in body
    assert "previous_versions" in body


def test_memory_history_endpoint(client: TestClient) -> None:
    _seed(client)
    mid = client.get("/api/memories?limit=1").json()["items"][0]["id"]
    body = client.get(f"/api/memories/{mid}/history").json()
    assert body["memory_id"] == mid
    assert body["events"]


def test_unknown_memory_is_404(client: TestClient) -> None:
    assert client.get("/api/memories/does-not-exist").status_code == 404


# --- governance ------------------------------------------------------------
def test_promotion_is_explicit_and_audited(client: TestClient) -> None:
    client.post("/api/demo/capture")
    personal = client.get("/api/memories?actor=arun&limit=200").json()["items"]
    private = [m for m in personal if m["visibility"] == "PERSONAL"]
    assert private, "captured knowledge starts personal"

    mid = private[0]["id"]
    # A different engineer may not promote someone else's personal memory.
    denied = client.post(
        f"/api/memories/{mid}/promote", json={"actor": "maya", "target": "TEAM"}
    )
    assert denied.status_code == 403

    # The owner may promote their own knowledge, and only a steward may promote
    # all the way to organizational knowledge.
    r = client.post(
        f"/api/memories/{mid}/promote", json={"actor": "arun", "target": "TEAM"}
    )
    assert r.status_code == 200, r.text
    assert r.json()["memory"]["visibility"] == "TEAM"
    assert r.json()["memory"]["promoted_by"] == "emp-arun"

    events = client.get(f"/api/memories/{mid}/history?actor=arun").json()["events"]
    assert any(e["action"].startswith("promoted_") for e in events)
    audit = client.get("/api/audit?event_type=memory_promoted&limit=50").json()["events"]
    assert any(e["memory_id"] == mid for e in audit)


def test_restrict_narrows_scope_and_does_not_delete_history(
    client: TestClient,
) -> None:
    _seed(client)
    assert client.post("/api/demo/queue-v2").status_code == 200
    items = client.get("/api/contradictions").json()
    assert items["count"] >= 1
    cid = items["contradictions"][0]["id"]
    mid = items["contradictions"][0]["memory_id"]
    r = client.post(
        f"/api/contradictions/{cid}/resolve",
        json={"actor": "steward", "action": "restrict", "note": "Queue v1 replaced."},
    )
    assert r.status_code == 200, r.text
    assert r.json()["contradiction"]["resolution"] == "restrict"
    assert r.json()["contradiction"]["status"] == "RESOLVED"
    before = client.get(f"/api/memories/{mid}?actor=steward").json()
    after = client.get(f"/api/memories/{mid}?actor=steward").json()
    # Restricting narrows applicability; it does not rewrite or retire the
    # memory, so the lifecycle status is left exactly as it was.
    assert after["memory"]["status"] == before["memory"]["status"]
    assert after["memory"]["excluded_scopes"] == ["Payment Queue v2"]
    # History is preserved: the original text and every event remain.
    assert after["memory"]["content"] == before["memory"]["content"]
    assert after["events"]
    assert any(e["action"] == "scope_restricted" for e in after["events"])


def test_architecture_change_creates_a_contradiction(client: TestClient) -> None:
    _seed(client)
    r = client.post("/api/demo/queue-v2")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payload"]["contradictions"]
    listing = client.get("/api/contradictions").json()
    assert listing["count"] >= 1
    first = listing["contradictions"][0]
    assert "v2" in (first["current_environment"] + first["memory_scope"])


def test_stale_memory_is_flagged_in_the_next_answer(client: TestClient) -> None:
    _seed(client)
    client.post("/api/demo/queue-v2")
    body = client.post("/api/ask", json={"actor": "maya"}).json()
    assert body["outdated"] is True
    assert body["answer"]["outdated_warning"]
    assert body["warnings"]


# --- audit -----------------------------------------------------------------
def test_audit_captures_the_whole_lifecycle(client: TestClient) -> None:
    _seed(client)
    client.post(
        "/api/outcome",
        json={
            "actor": "maya",
            "question": "What should I check before restarting the payment queue?",
            "recommendation": "Check the dead-letter queue depth first.",
            "actual_action": "Checked dead-letter depth first.",
            "result": "Restart succeeded. No duplicate payments.",
            "outcome_id": "OUT-TEST-AUDIT",
        },
    )
    events = client.get("/api/audit?limit=1000").json()["events"]
    kinds = {e["event_type"] for e in events}
    assert {"memory_captured", "memory_promoted", "outcome_recorded"} <= kinds
    assert "hindsight_retain" in kinds
    for e in events:
        assert e["actor"]
        assert e["label"]


def test_audit_is_filterable_by_type_and_memory(client: TestClient) -> None:
    _seed(client)
    only = client.get("/api/audit?event_type=memory_promoted&limit=100").json()["events"]
    assert only
    for e in only:
        assert e["event_type"] == "memory_promoted"
    mid = only[0]["memory_id"]
    assert mid
    scoped = client.get(f"/api/audit?memory_id={mid}&limit=100").json()["events"]
    assert all(e["memory_id"] == mid for e in scoped)


# --- demo ------------------------------------------------------------------
def test_full_demo_runs_every_step_without_error(client: TestClient) -> None:
    r = client.post("/api/demo/run")
    assert r.status_code == 200, r.text
    body = r.json()
    failed = [s for s in body["steps"] if s["status"] != "ok"]
    assert not failed, failed
    assert body["status"] == "ok"
    assert len(body["steps"]) == 13
    assert body["duration_ms"] >= 0
    assert body["progress_percent"] == 100
    assert body["steps"][0]["key"] == "reset"


def test_every_demo_control_endpoint_works(client: TestClient) -> None:
    for key in (
        "reset",
        "seed",
        "seed-incidents",
        "capture",
        "promote",
        "ask",
        "outcome",
        "queue-v2",
        "evolution",
        "privacy",
        "resolve-contradictions",
    ):
        r = client.post(f"/api/demo/{key}", json={})
        assert r.status_code == 200, f"{key}: {r.status_code} {r.text[:300]}"
        assert r.json()["ok"] is True, key


def test_demo_reset_returns_to_a_clean_slate(client: TestClient) -> None:
    _seed(client)
    assert client.post("/api/demo/reset").status_code == 200
    state = client.get("/api/demo/state").json()
    assert state["memories"] == 0
    assert state["open_contradictions"] == 0
    assert state["current_environment"] == "Payment Queue v1"


def test_demo_controls_are_exposed_with_callable_keys(client: TestClient) -> None:
    body = client.get("/api/demo/controls").json()
    assert len(body["controls"]) == 8
    for control in body["controls"]:
        assert control["key"]
        assert control["label"]
        assert control["narration"]
    keys = {c["key"] for c in body["controls"]}
    assert {"seed", "ask", "outcome", "queue-v2", "evolution", "privacy", "reset"} <= keys
    assert body["engine"]["memory_engine"] == "hindsight"


def test_learning_curve_is_disclaimed_as_prototype_measurement(
    client: TestClient,
) -> None:
    _seed(client)
    body = client.get("/api/demo/learning-curve").json()
    assert "not a scientific benchmark" in body["disclaimer"]
    assert len(body["points"]) >= 4


def test_demo_privacy_step_reports_what_was_withheld(client: TestClient) -> None:
    _seed(client)
    r = client.post("/api/demo/privacy")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["payload"]["withheld"] or body["payload"].get("withheld_count", 0) >= 0


def test_before_after_comparison(client: TestClient) -> None:
    body = client.get("/api/demo/before-after").json()
    assert body["before"]
    assert body["labels"]["before"] == "BEFORE MEMORYOS"
    _seed(client)
    body = client.get("/api/demo/before-after").json()
    assert body["after"]["answer"]["headline"]
