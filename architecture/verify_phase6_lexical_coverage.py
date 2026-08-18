#!/usr/bin/env python3
"""Phase 6 lexical coverage and easy-word reliability gate."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "architecture" / "phase6_lexical_coverage_manifest.json"


def load(name: str, path: Path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest.get("phase") == 6, "wrong Phase-6 manifest")
    require(manifest.get("status") in {"IMPLEMENTATION_IN_PROGRESS", "PASS"}, "invalid Phase-6 status")
    require(manifest.get("engine_count") == 44 and manifest.get("new_engine_count") == 0, "Phase 6 must not invent engine #45")
    phase5 = json.loads((ROOT / "architecture" / "phase5_visual_packaging_manifest.json").read_text(encoding="utf-8"))
    require(phase5.get("status") == "PASS", "Phase 5 is no longer PASS")

    data_manifest_path = ROOT / "data" / "phase6-data-manifest.json"
    require(data_manifest_path.is_file(), "Phase-6 lexical data was not materialized")
    data_manifest = json.loads(data_manifest_path.read_text(encoding="utf-8-sig"))
    require(data_manifest.get("unicode_emoji_version") == "17.0", "wrong Unicode Emoji dataset")
    require(int(data_manifest.get("unicode_rgi_count", 0)) > 3000, "Unicode RGI dataset is unexpectedly incomplete")
    require(data_manifest.get("oewn_edition") == "2025", "wrong Open English WordNet edition")

    lexical = load("_phase6_verify_lexical", ROOT / "📚" / "📖")
    vocab = load("_phase6_verify_vocab", ROOT / "📚" / "📚")
    universe = load("_phase6_verify_universe", ROOT / "🌐" / "🌐")
    resolver = lexical.resolver()
    require(resolver.emoji.version == "17.0", "lexical resolver did not load Unicode Emoji 17.0")
    require(resolver.emoji_count == int(data_manifest["unicode_rgi_count"]), "emoji count must come from the official dataset")
    require(vocab.official_emoji_count() == resolver.emoji_count, "Vocabulary and lexical emoji counts disagree")
    snapshot = universe.EmojiUniverseEngine().snapshot
    require(snapshot.rgi_complete and snapshot.version == "17.0", "Emoji Universe is not using official RGI authority")
    require(snapshot.count == resolver.emoji_count, "Emoji Universe count disagrees with lexical authority")

    lemma_count = sum(len(rows) for rows in resolver.wordnet.index.values())
    require(resolver.wordnet.available, "Open English WordNet is unavailable")
    require(lemma_count > 100_000, f"lexical index too small: {lemma_count}")

    direct_expectations = {
        "robot": "🤖",
        "fox": "🦊",
        "laptop": "💻",
        "chair": "🪑",
        "dog": "🐕",
        "credit card": "💳",
        "toothbrush": "🪥",
        "fire engine": "🚒",
    }
    for word, expected in direct_expectations.items():
        result = resolver.resolve(word, word)
        require(result.resolved, f"easy word failed lexical resolution: {word} ({result.status})")
        require(result.expression == expected, f"wrong direct emoji for {word}: {result.expression!r}")
        require(result.semantic_loss <= 0.10, f"direct word has excessive semantic loss: {word}")

    dog = resolver.resolve("dog", "the dog runs")
    dogs = resolver.resolve("dogs", "the dogs run")
    require(dog.resolved and dogs.resolved and dog.expression == dogs.expression, "plural morphology failed for dogs")
    require(resolver.resolve("zxqvplmno", "zxqvplmno").status == "unresolved", "nonsense must remain unresolved")
    scarcity = resolver.resolve("scarcity", "scarcity of food")
    require(scarcity.expression != "🚗", "naive substring matching incorrectly mapped scarcity to car")

    easy_words = (
        "robot fox laptop chair dog cat mouse rabbit bear panda frog monkey chicken penguin bird eagle duck owl wolf horse cow pig hamster"
        " apple banana grapes watermelon lemon peach strawberry bread cheese pizza hamburger egg cookie cake coffee tea soccer basketball football baseball"
        " car taxi bus ambulance bicycle motorcycle airplane rocket helicopter train metro ship anchor fuel house school hospital bank hotel church tent"
        " phone keyboard printer camera television radio light bulb battery hammer wrench key lock bell book pencil memo package gift balloon trophy medal"
    ).split()
    unique_easy = tuple(dict.fromkeys(easy_words))
    resolved = sum(1 for word in unique_easy if resolver.resolve(word, word).resolved)
    rate = resolved / max(1, len(unique_easy))
    require(rate >= 0.80, f"easy_word_resolution_rate too low: {rate:.3f} ({resolved}/{len(unique_easy)})")

    abc = load("_phase6_verify_abc", ROOT / "🔤➡️😀" / "🔤➡️😀")
    engine = abc.ABCToEmojiEngine()
    for word, expected in {"fox": "🦊", "laptop": "💻", "chair": "🪑", "robot": "🤖"}.items():
        result = engine.translate(word, cross_verify=False, emit=False)
        require(expected in result.winner, f"full translator missed easy word {word}: {result.winner}")
        require(result.metrics.get("unknown_count") == 0, f"easy word remained unknown: {word}")
        require(int(result.metrics.get("phase6_lexical_resolutions", 0)) >= 1, f"Phase-6 lexical path not used for {word}")

    vocab_source = (ROOT / "📚" / "📚").read_text(encoding="utf-8")
    bridge_source = (ROOT / "🔤➡️😀" / "🧠").read_text(encoding="utf-8")
    main_source = (ROOT / "main.js").read_text(encoding="utf-8")
    lexical_source = (ROOT / "📚" / "📖").read_text(encoding="utf-8")
    require("!= 501" not in vocab_source and "== 501" not in vocab_source, "fixed 501 invariant still exists in Vocabulary")
    require("includes(root)" not in bridge_source and ".includes(root)" not in bridge_source, "naive substring root matching leaked into lexical bridge")
    require("EL_HYPERNYMS" not in main_source and "processELToken" not in main_source, "semantic dictionary leaked into main.js")
    for marker in ("OllamaConnector", "qwen2.5vl", "chat_internal", "_ollama", "urllib.request"):
        require(marker.lower() not in lexical_source.lower(), f"provider coupling leaked into lexical resolver: {marker}")

    print(f"PHASE6_OK emoji={resolver.emoji_count} oewn_lemmas={lemma_count} easy_word_resolution_rate={rate:.3f} ({resolved}/{len(unique_easy)})")


if __name__ == "__main__":
    main()
