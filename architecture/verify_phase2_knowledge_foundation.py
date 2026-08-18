#!/usr/bin/env python3
"""Phase 2 deterministic knowledge-foundation verification with later authority compatibility."""
from __future__ import annotations

from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "architecture" / "phase2_knowledge_foundation_manifest.json"


def load(name: str, path: Path):
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
    require(manifest["phase"] == 2, "wrong phase manifest")
    require(manifest["status"] == "PASS", "Phase 2 authority state must remain PASS")
    require(manifest["source_present_target_engines"] == 30, "source-present target count must be 30")
    require(manifest["planned_only_target_engines"] == 14, "planned-only target count must be 14")
    require(len(manifest["implemented"]) == 6, "Phase 2 must implement six foundation engines")

    for item in manifest["implemented"]:
        path = ROOT / item["source_path"]
        require(path.is_file(), f"missing Phase-2 source: {path}")
        source = path.read_text(encoding="utf-8")
        for forbidden in ("OllamaConnector", "qwen2.5vl", "ForgeyConnector", "chat_internal", "generate_internal"):
            require(forbidden not in source, f"provider coupling in {item['id']}: {forbidden}")

    core = load("_p2_core", ROOT / "⚙️" / "⚙️")
    vocab = load("_p2_vocab", ROOT / "📚" / "📚")
    canon = load("_p2_canon", ROOT / "🧷" / "🧷")
    universe = load("_p2_universe", ROOT / "🌐" / "🌐")
    provenance = load("_p2_provenance", ROOT / "📜" / "📜")
    evidence = load("_p2_evidence", ROOT / "📊" / "📊")
    versioning = load("_p2_versioning", ROOT / "🗃️" / "🗃️")
    integrity = load("_p2_integrity", ROOT / "🧿" / "🧿")

    seed = vocab.SEMANTIC_BASE_SYMBOLS
    require(seed and len(set(seed)) == len(seed), "semantic seed invariant changed")
    if "canonical_vocabulary_count" in manifest:
        require(int(manifest["canonical_vocabulary_count"]) == len(seed), "historical Phase-2 semantic-seed metadata changed")

    canonicalizer = canon.EmojiCanonicalizationEngine()
    sun = canonicalizer.canonicalize_unit("☀")
    require(sun.valid and sun.canonical == "☀️" and sun.changed, "presentation alias canonicalization failed")
    keycap = canonicalizer.canonicalize_unit("1\u20e3")
    require(keycap.valid and keycap.canonical == "1️⃣", "keycap canonicalization failed")
    family = canonicalizer.canonicalize_unit("👨‍👩‍👧‍👦")
    require(family.valid and len(core.split_graphemes(family.canonical)) == 1, "ZWJ grapheme canonicalization failed")
    require(not canonicalizer.canonicalize_unit("abc").valid, "letters must not become emoji units")

    current = universe.EmojiUniverseEngine()
    require(current.snapshot.count > len(seed), "emoji universe must exceed the stable semantic seed")
    if (ROOT / "data" / "unicode" / "emoji-test.txt").is_file():
        require(current.snapshot.rgi_complete, "materialized official emoji data must be RGI complete")
        require(current.snapshot.version == "17.0", "unexpected released Unicode Emoji version")
        require(current.snapshot.count == vocab.official_emoji_count(), "Vocabulary and Emoji Universe disagree")
    else:
        require(not current.snapshot.rgi_complete, "fallback universe must not claim RGI completeness")
    require(current.contains("😀") and current.contains("☀"), "universe membership/canonicalization failed")

    fixture = """# emoji-test.txt\n# Version: 17.0\n1F600 ; fully-qualified # 😀 grinning face\n263A FE0F ; fully-qualified # ☺️ smiling face\n263A ; unqualified # ☺ smiling face\n1F3FB ; component # 🏻 light skin tone\n1F468 200D 1F469 200D 1F467 200D 1F466 ; fully-qualified # 👨‍👩‍👧‍👦 family\n"""
    rgi = universe.EmojiUniverseEngine.from_emoji_test(fixture)
    require(rgi.snapshot.rgi_complete and rgi.snapshot.version == "17.0", "emoji-test RGI/version contract failed")
    require(rgi.snapshot.fully_qualified_count == 3 and rgi.snapshot.component_count == 1, "emoji-test status counting failed")
    require(rgi.snapshot.count == 4 and rgi.contains("☺️") and not rgi.contains("☹️"), "emoji-test filtering failed")

    fixed_time = datetime(2026, 8, 12, 23, 0, tzinfo=timezone.utc)
    ledger = provenance.ProvenanceLedgerEngine(clock=lambda: fixed_time)
    p1 = ledger.append(record_id="p1", claim_id="c1", source_kind="deterministic", source_ref="test", validation_status="pass")
    require(p1.created_at.endswith("Z") and ledger.for_claim("c1") == (p1,), "provenance append/query failed")
    duplicate_rejected = False
    try:
        ledger.append(record_id="p1", claim_id="c1", source_kind="deterministic", source_ref="duplicate")
    except ValueError:
        duplicate_rejected = True
    require(duplicate_rejected, "duplicate provenance ID must be rejected")
    provider_identity_rejected = False
    try:
        ledger.append(record_id="p2", claim_id="c2", source_kind="provider", source_ref="assist")
    except ValueError:
        provider_identity_rejected = True
    require(provider_identity_rejected, "provider provenance must identify provider/model")

    evidence_engine = evidence.EvidenceConfidenceEngine()
    evidence_engine.record(evidence_id="e1", claim_id="c1", polarity="positive", weight=0.9, source="validation", reason="roundtrip-pass", provenance_id="p1")
    evidence_engine.record(evidence_id="e2", claim_id="c1", polarity="negative", weight=0.1, source="countercheck", reason="minor-ambiguity", provenance_id="p1")
    confidence = evidence_engine.confidence("c1")
    require(confidence.evidence_count == 2 and abs(confidence.confidence - 0.9) < 1e-9, "confidence aggregation failed")

    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "knowledge.json"
        versions = versioning.KnowledgeVersioningRollbackEngine(path=path, clock=lambda: fixed_time)
        v1 = versions.commit({"claims": {"c1": {"expression": "🔥"}}}, change_ids=("c1",), label="v1")
        v2 = versions.commit({"claims": {"c1": {"expression": "🔥➡️🚀"}}}, change_ids=("c1",), label="v2")
        require(v1.version_id == "1" and v2.parent_id == "1" and v1.state_hash != v2.state_hash, "knowledge version lineage/hash failed")
        v3 = versions.rollback("1")
        require(v3.version_id == "3" and v3.parent_id == "2" and versions.snapshot_for("3") == versions.snapshot_for("1"), "rollback must create new history")
        restored = versioning.KnowledgeVersioningRollbackEngine(path=path, clock=lambda: fixed_time)
        require(restored.current is not None and restored.current.version_id == "3" and len(restored.versions) == 3, "knowledge version persistence failed")

    guard = integrity.KnowledgeIntegrityEngine()
    valid_claim = {"claim_id": "c1", "concept": "deploy", "expression": "🚀", "maturity": "canonical"}
    good = guard.assess(valid_claim, confidence=confidence, provenance=ledger.for_claim("c1"), existing_claims=())
    require(good.passed, f"valid claim unexpectedly blocked: {good.issues}")
    missing = guard.assess({"claim_id": "c2", "concept": "converter", "expression": "🔄", "maturity": "discovered"})
    require(missing.status == "fail", "missing provenance must fail integrity")
    conflict = guard.assess(valid_claim, confidence=confidence, provenance=ledger.for_claim("c1"), existing_claims=({"claim_id":"c9","concept":"deploy","expression":"📤","maturity":"canonical"},))
    require(conflict.status == "fail" and any(item.code == "concept-conflict" for item in conflict.issues), "canonical conflict detection failed")

    print(f"✅📚2️⃣ 🌐{current.snapshot.count}✅ 📊✅ 🧿✅ 🧷✅ 📜✅ 🗃️✅ seed={len(seed)} 🤖❌")


if __name__ == "__main__":
    main()
