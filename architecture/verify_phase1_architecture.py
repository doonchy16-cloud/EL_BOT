"""Phase 1 architecture-only verification for the EL Bot 44-engine target contract.

This gate must not import or execute planned engines. It validates architecture
metadata, current source presence, boundary locks, and dependency consistency.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "architecture" / "phase1_44_engine_registry.json"
PLANNING = ROOT / "PLANNING_EL_FOREVER_EXPANDING_LANGUAGE_ARCHITECTURE_2026-08-12.md"
CONTRACTS = ROOT / "architecture" / "PHASE_1_44_ENGINE_CONTRACTS.md"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def assert_acyclic(graph: dict[str, tuple[str, ...]]) -> None:
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        marker = state.get(node, 0)
        if marker == 2:
            return
        if marker == 1:
            try:
                start = stack.index(node)
            except ValueError:
                start = 0
            cycle = " -> ".join(stack[start:] + [node])
            raise AssertionError(f"dependency cycle: {cycle}")
        state[node] = 1
        stack.append(node)
        for dependency in graph[node]:
            visit(dependency)
        stack.pop()
        state[node] = 2

    for node in graph:
        visit(node)


def main() -> None:
    require(REGISTRY.is_file(), "44-engine registry missing")
    require(PLANNING.is_file(), "Owner-locked planning authority missing")
    require(CONTRACTS.is_file(), "Phase 1 contracts missing")

    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    engines = payload.get("engines")
    require(isinstance(engines, list), "engines must be a list")
    require(payload.get("engine_count") == 44 == len(engines), "engine count must be 44")
    require(payload.get("existing_engine_count") == 24, "existing count must be 24")
    require(payload.get("planned_engine_count") == 20, "planned count must be 20")

    ids = [str(item.get("id", "")) for item in engines]
    runtime_markers = [str(item.get("runtime_marker", "")) for item in engines]
    require(len(ids) == len(set(ids)) == 44, "engine IDs must be unique")
    require(all(ids), "engine ID missing")
    require(len(runtime_markers) == len(set(runtime_markers)) == 44, "runtime markers must be unique")
    require(all(runtime_markers), "runtime marker missing")

    by_id = {str(item["id"]): item for item in engines}
    existing = [item for item in engines if str(item["id"]).startswith("E")]
    planned = [item for item in engines if str(item["id"]).startswith("N")]
    require(len(existing) == 24 and len(planned) == 20, "E/N registry partition incorrect")

    for item in existing:
        path = item.get("source_path")
        require(item.get("implementation_state") == "source-present", f"{item['id']} must be source-present")
        require(isinstance(path, str) and path, f"{item['id']} source path missing")
        require((ROOT / path).is_file(), f"{item['id']} source file missing: {path}")

    for item in planned:
        require(item.get("implementation_state") == "planned-only", f"{item['id']} must remain planned-only")
        require(item.get("source_path") is None, f"{item['id']} must not claim source implementation")

    graph: dict[str, tuple[str, ...]] = {}
    known = set(ids)
    for item in engines:
        engine_id = str(item["id"])
        dependencies = tuple(str(value) for value in item.get("depends_on", []))
        require(engine_id not in dependencies, f"{engine_id} self dependency")
        unknown = [value for value in dependencies if value not in known]
        require(not unknown, f"{engine_id} unknown dependencies: {unknown}")
        graph[engine_id] = dependencies
    assert_acyclic(graph)

    expected_collisions = {"N07": "🧫", "N10": "🧿", "N11": "♻️", "N20": "🧺"}
    require(payload.get("runtime_marker_collision_resolutions") == expected_collisions, "collision resolutions changed")
    for engine_id, runtime_marker in expected_collisions.items():
        require(by_id[engine_id]["runtime_marker"] == runtime_marker, f"{engine_id} collision resolution drift")
    require(by_id["E07"]["runtime_marker"] == "🧪", "Diagnostics must retain 🧪")
    require(by_id["E18"]["runtime_marker"] == "🛡️", "Reliability must retain 🛡️")
    require(by_id["E22"]["runtime_marker"] == "🔄", "Updater must retain 🔄")

    rules = payload.get("rules") or {}
    for locked_rule in (
        "deterministic_first",
        "ai_escalation_only_on_fail",
        "hold_does_not_escalate",
        "abc_to_emoji_direct_provider_dependency_forbidden",
        "raw_ai_release_forbidden",
        "canonical_501_is_not_universe_limit",
        "complete_search_means_declared_finite_space",
        "silent_heuristic_pruning_forbidden",
        "learning_requires_provenance_validation_and_graduation",
    ):
        require(rules.get(locked_rule) is True, f"locked rule disabled: {locked_rule}")

    # Direct provider coupling is architecturally forbidden for ABC -> Emoji.
    require("E14" not in graph["E23"] and "E15" not in graph["E23"], "ABC -> Emoji may not depend on connector/orchestration")
    require("E14" in graph["E15"], "Forgey Orchestration must route through Connector")
    require("E15" not in graph["E14"], "Connector may not own escalation policy")

    abc_source = (ROOT / str(by_id["E23"]["source_path"])).read_text(encoding="utf-8")
    for forbidden_provider_token in ("OllamaConnector", "_ollama", "qwen2.5vl", "ForgeyConnector"):
        require(forbidden_provider_token not in abc_source, f"direct provider coupling found in ABC -> Emoji: {forbidden_provider_token}")

    # Provider adapters exist outside the 44-engine count and remain replaceable.
    require((ROOT / "🦙" / "🦙").is_file(), "temporary Ollama adapter missing")
    require(all(item["name"] != "Ollama Engine" for item in engines), "Ollama must not become a 45th engine")

    # Phase 1 must not mutate the canonical 501 authority.
    vocabulary_source = (ROOT / "📚" / "📚").read_text(encoding="utf-8")
    require("len(CANONICAL_SYMBOLS) != 501" in vocabulary_source, "current 501 vocabulary invariant changed during Phase 1")

    print("✅🧱44 🔒24+20 🔗✅ 🌳✅ 🤖❌➡️🔤➡️😀")


if __name__ == "__main__":
    main()
