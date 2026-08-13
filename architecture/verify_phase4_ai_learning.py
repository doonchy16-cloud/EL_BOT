#!/usr/bin/env python3
"""Phase 4 AI-fallback and forever-learning verification gate."""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import tempfile
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "architecture" / "phase4_ai_learning_manifest.json"


def load(name: str, path: Path):
    if name in sys.modules:
        return sys.modules[name]
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError("module spec unavailable")
    module = module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest["phase"] == 4, "wrong Phase-4 manifest")
    require(manifest["status"] in {"IMPLEMENTATION_IN_PROGRESS", "PASS"}, "invalid Phase-4 authority state")
    require(manifest["source_present_target_engines"] == 44, "source-present target must be 44")
    require(manifest["planned_only_target_engines"] == 0, "planned-only target must be zero")
    require(manifest["canonical_base_vocabulary_count"] == 501, "base 501 authority changed")
    require(len(manifest["implemented"]) == 5, "Phase 4 must implement five engines")

    for item in manifest["implemented"]:
        require((ROOT / item["source_path"]).is_file(), "missing Phase-4 source: " + item["source_path"])

    abc_source = (ROOT / "🔤➡️😀" / "🔤➡️😀").read_text(encoding="utf-8")
    orchestration_source = (ROOT / "✦" / "✦").read_text(encoding="utf-8")
    facade_source = (ROOT / "↔️" / "↔️").read_text(encoding="utf-8")
    provider_source = (ROOT / "🔌" / "🧠").read_text(encoding="utf-8")
    for token in ("OllamaConnector", "qwen2.5vl", "urllib.request", "chat_json_internal", "generate_internal"):
        require(token not in abc_source, "ABC engine provider coupling: " + token)
    for token in ("OllamaConnector", "qwen2.5vl", "urllib.request"):
        require(token not in orchestration_source, "orchestration provider coupling: " + token)
    require("OllamaConnector" not in facade_source and "qwen2.5vl" not in facade_source, "facade must remain provider-neutral")
    require("OllamaConnector" in provider_source and "chat_json_internal" in provider_source, "current provider adapter is not isolated")

    vocab = load("_p4_vocab", ROOT / "📚" / "📚")
    connector_mod = load("_p4_connector", ROOT / "🔌" / "🔌")
    orchestration_mod = load("_p4_orchestration", ROOT / "✦" / "✦")
    validation_mod = load("_p4_validation", ROOT / "🧾" / "🧾")
    abc_mod = load("_p4_abc", ROOT / "🔤➡️😀" / "🔤➡️😀")
    emoji_mod = load("_p4_emoji", ROOT / "😀➡️🔤" / "😀➡️🔤")
    bidi_mod = load("_p4_bidi", ROOT / "↔️" / "↔️")
    learning_mod = load("_p4_learning", ROOT / "🧑‍🏫" / "🧠")
    graduation_mod = load("_p4_grad", ROOT / "🎓" / "🎓")
    generalization_mod = load("_p4_gen", ROOT / "🧬" / "🧬")
    revalidation_mod = load("_p4_reval", ROOT / "♻️" / "♻️")
    analytics_mod = load("_p4_analytics", ROOT / "📈" / "📈")
    consolidation_mod = load("_p4_consolidation", ROOT / "🧺" / "🧺")
    provider_mod = load("_p4_provider_adapter", ROOT / "🔌" / "🧠")

    require(len(vocab.CANONICAL_SYMBOLS) == 501 and len(set(vocab.CANONICAL_SYMBOLS)) == 501, "canonical base vocabulary changed")

    orch = orchestration_mod.OrchestrationEngine()
    require(not orch.should_escalate("pass") and not orch.should_escalate("hold") and orch.should_escalate("fail"), "FAIL-only escalation policy broken")

    # Internal provider data must never be reachable through the public EL connector invocation.
    internal_calls = {"count": 0}
    connectors = connector_mod.ConnectorEngine()
    def internal_handler(payload):
        internal_calls["count"] += 1
        return {"secret_raw": "provider prose", "echo": dict(payload)}
    connectors.register_internal("🦙", internal_handler, probe=lambda: True, provider="stub", model="stub-model")
    require(connectors.invoke("🦙", "🔥") == "🟡🔌❓", "public connector leaked internal provider")
    internal_result = connectors.invoke_internal("🦙", {"source": "x"})
    require(internal_result.ok and internal_result.called and internal_calls["count"] == 1 and internal_result.payload["secret_raw"] == "provider prose", "internal connector path failed")

    # Direct assisted validator: canonical/reversible candidate can pass; malformed EL cannot.
    validator = validation_mod.ValidationEngine()
    abc_engine = abc_mod.ABCToEmojiEngine(); emoji_engine = emoji_mod.EmojiToABCEngine()
    candidate = "📥➡️🔄➡️📤"
    definition = "input restart output"
    reverse = emoji_engine.translate(candidate, verifier=abc_engine, cross_verify=True, emit=False)
    forward = abc_engine.translate(reverse.winner, verifier=emoji_engine, cross_verify=True, emit=False)
    valid_report = validator.validate_assisted("transmuter", definition, candidate, reverse_text=reverse.winner, deterministic_metrics=dict(forward.metrics))
    require(valid_report.releasable, "strict assisted fixture did not pass: " + repr(valid_report.metrics) + " " + repr(valid_report.reasons))
    invalid_report = validator.validate_assisted("transmuter", definition, "abc", reverse_text="", deterministic_metrics={"quality_status":"fail","coverage":0,"roundtrip":0,"unknown_count":1})
    require(not invalid_report.releasable and invalid_report.status.value == "fail", "malformed assisted candidate was releasable")

    class StubConnector:
        def __init__(self, payload: dict):
            self.payload = payload; self.calls = 0
        def invoke_internal(self, marker: str, payload: dict):
            self.calls += 1
            return connector_mod.InternalConnectorResult(marker, True, True, "stub", "semantic-stub-v1", dict(self.payload), "")

    with tempfile.TemporaryDirectory() as folder:
        learning = learning_mod.LearningCoordinator(Path(folder) / "learn.json")
        good_connector = StubConnector({"resolvable": True, "definition": definition, "candidate_el": candidate, "confidence": 0.97})
        engine = bidi_mod.TranslationEngine(learning=learning, connector=good_connector)

        # PASS source: zero provider calls.
        passed = engine.ranked_to_el("hi", emit=False)
        require(passed.metrics.get("quality_status") == "pass" and good_connector.calls == 0 and engine.provider_call_count == 0, "PASS path called provider")

        # Find a real deterministic HOLD and prove it also does not call provider.
        hold_source = None
        for sample in ("restart server zorb", "restart the local server zorb", "server warning zorb", "deploy package zorb"):
            probe = abc_engine.translate(sample, verifier=emoji_engine, cross_verify=True, emit=False)
            if probe.metrics.get("quality_status") == "hold":
                hold_source = sample; break
        require(hold_source is not None, "no deterministic HOLD fixture found")
        before = good_connector.calls
        held = engine.ranked_to_el(hold_source, emit=False)
        require(held.metrics.get("quality_status") == "hold" and good_connector.calls == before, "HOLD path called provider")

        # Genuine FAIL: exactly one provider call; only validated candidate is released.
        failed = abc_engine.translate("transmuter", verifier=emoji_engine, cross_verify=True, emit=False)
        require(failed.metrics.get("quality_status") == "fail", "FAIL fixture no longer fails deterministically")
        assisted = engine.ranked_to_el("transmuter", emit=False)
        require(good_connector.calls == before + 1 and engine.provider_call_count == 1, "FAIL did not trigger exactly one provider call")
        require(assisted.winner == candidate and assisted.metrics.get("quality_status") == "pass" and assisted.metrics.get("ai_assisted") is True, "validated assisted candidate not released")
        require(assisted.metrics.get("raw_provider_exposed") is False, "raw-provider exposure flag broken")
        serialized = json.dumps(assisted.as_dict(), ensure_ascii=False)
        require(definition not in serialized and "semantic-stub-v1" in serialized and "stub" in serialized, "raw semantic definition leaked or provider attribution missing")

        claims = learning.claims
        require(len(claims) == 1 and claims[0]["maturity"] == "discovered", "single provider success advanced too far")
        require(all("definition" not in key for claim in claims for key in claim.keys()), "raw provider definition stored in claim")

        # Malformed/unverifiable help is rejected, original deterministic failure remains safe.
        bad_connector = StubConnector({"resolvable": True, "definition": "flibbertigibbet", "candidate_el": "abc", "confidence": 0.99})
        bad_learning = learning_mod.LearningCoordinator(Path(folder) / "bad.json")
        bad_engine = bidi_mod.TranslationEngine(learning=bad_learning, connector=bad_connector)
        rejected = bad_engine.ranked_to_el("gobbledygook", emit=False)
        require(bad_connector.calls == 1 and rejected.metrics.get("quality_status") == "fail" and rejected.winner != "abc", "invalid provider assistance escaped")
        require(len(bad_learning.episodes) == 1 and bad_learning.episodes[0]["accepted"] is False, "rejected provider attempt was not retained")
        require("flibbertigibbet" not in json.dumps(bad_learning.episodes, ensure_ascii=False), "raw provider definition leaked into negative episode")

        # Full graduation requires provider + user + experiment + counterexample + revalidation evidence.
        claim_id = claims[0]["claim_id"]
        two = learning.record_user_selection("transmuter", candidate)
        require(two is not None and two.maturity == "provisional", "user evidence did not move to provisional")
        three = learning.record_experiment(claim_id, passed=True, counterexample=False)
        require(three.maturity == "validated", "cross-source experiment did not validate")
        four = learning.record_experiment(claim_id, passed=True, counterexample=True)
        require(four.maturity == "validated", "counterexample pass advanced prematurely")
        five = learning.record_revalidation(claim_id, status="pass", reasons=("roundtrip-pass",))
        require(five.maturity == "canonical", "full graduation contract did not reach canonical")
        require(len(learning.claims[0]["evidence"]) >= 5 and len(learning.claims[0]["provenance"]) >= 5, "graduation lost evidence/provenance")

        # Mature learned knowledge eliminates the next provider call.
        never_connector = StubConnector({"resolvable": False, "definition": "", "candidate_el": "", "confidence": 0.0})
        learned_engine = bidi_mod.TranslationEngine(learning=learning, connector=never_connector)
        learned_result = learned_engine.ranked_to_el("transmuter", emit=False)
        require(learned_result.winner == candidate and learned_result.metrics.get("learned_assisted") is True, "mature learned mapping not reused")
        require(never_connector.calls == 0 and learned_engine.provider_call_count == 0, "learned mapping failed to eliminate provider call")

        # Failed revalidation can move strong knowledge backward.
        demoted = learning.record_revalidation(claim_id, status="fail", reasons=("adversarial-regression",))
        require(demoted.maturity in {"provisional", "discovered"}, "failed revalidation did not demote knowledge")

        # Versioning is real and rollback creates a new version instead of deleting history.
        version_count = len(learning.versioner.versions)
        require(version_count >= 6, "learning mutations were not versioned")
        target_version = learning.versioner.versions[0].version_id
        learning.rollback(target_version)
        require(len(learning.versioner.versions) == version_count + 1, "rollback did not create reversible lineage")

    # Individual Phase-4 engines: no hidden promotion authority.
    grad = graduation_mod.KnowledgeGraduationEngine()
    require(grad.process("🎓") == "✅🎓", "graduation engine status failed")

    general = generalization_mod.GeneralizationEngine().derive((
        {"claim_id":"g1","concept":"compile source","expression":"📥➡️🔄➡️📤","maturity":"validated","confidence":.93},
        {"claim_id":"g2","concept":"convert input","expression":"📥➡️🔄➡️📤","maturity":"canonical","confidence":.97},
    ))
    require(len(general.rules) == 1 and general.rules[0].status == "hypothesis", "generalization must produce a hypothesis only")

    reval = revalidation_mod.RevalidationEngine()
    reval_report = reval.revalidate(({"claim_id":"r1","maturity":"canonical"},{"claim_id":"r2","maturity":"validated"}), lambda claim: "pass" if claim["claim_id"] == "r1" else "fail")
    require(reval_report.outcomes[0].recommended_maturity == "canonical" and reval_report.outcomes[1].recommended_maturity == "discovered", "revalidation recommendations failed")

    analytics = analytics_mod.LearningAnalyticsEngine()
    analytics.record("deterministic_attempt", 4); analytics.record("deterministic_pass", 3); analytics.record("ai_attempt", 1); analytics.record("ai_accept", 1); analytics.record("learned_hit", 1)
    snap = analytics.snapshot()
    require(abs(snap.deterministic_success_rate - .75) < 1e-9 and abs(snap.ai_fallback_rate - .25) < 1e-9 and snap.ai_acceptance_rate == 1.0 and snap.learned_avoidance_rate == .5, "learning analytics math failed")

    consolidation = consolidation_mod.KnowledgeConsolidationEngine().consolidate((
        {"claim_id":"a","concept":"thing","expression":"🔥","sense_id":"s","evidence_ids":["e1"],"provenance_ids":["p1"]},
        {"claim_id":"b","concept":"thing","expression":"🔥","sense_id":"s","evidence_ids":["e2"],"provenance_ids":["p2"]},
        {"claim_id":"c","concept":"thing","expression":"🚀","sense_id":"s","evidence_ids":["e3"],"provenance_ids":["p3"]},
    ))
    require(consolidation.merged_groups == 1 and len(consolidation.conflicts) == 1, "knowledge consolidation did not merge and preserve conflict")
    merged = next(item for item in consolidation.consolidated if item.get("expression") == "🔥")
    require(set(merged["evidence_ids"]) == {"e1","e2"} and set(merged["provenance_ids"]) == {"p1","p2"}, "consolidation lost history")

    # Real local provider adapter sanity. Existing CI separately proves the model is installed.
    real_adapter = provider_mod.CurrentSemanticProviderAdapter()
    require(real_adapter.available(), "current qwen provider is unavailable")
    live = real_adapter.resolve({"source": "compiler"})
    require(set(live) == {"resolvable","definition","candidate_el","confidence"}, "live provider structured shape failed")
    require(isinstance(live["resolvable"], bool) and 0.0 <= live["confidence"] <= 1.0, "live provider structured types failed")
    if live["resolvable"]:
        require(bool(live["definition"].strip()), "live provider resolvable response lacks definition")

    print("✅✦🧠4️⃣ 44/44📦 🎓✅ 🧬✅ ♻️✅ 📈✅ 🧺✅ FAIL➡️✦✅ HOLD➡️🤖❌ PASS➡️🤖❌ 🧾✦✅ 📜📊🗃️✅ 🧑‍🏫➡️🤖⬇️✅ 🦙qwen2.5vl:7b✅")


if __name__ == "__main__":
    main()
