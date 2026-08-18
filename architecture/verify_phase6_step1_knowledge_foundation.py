#!/usr/bin/env python3
"""Phase 6 Step 1 knowledge-foundation verification gate."""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "architecture" / "phase6_step1_knowledge_foundation_manifest.json"
DATA_MANIFEST = ROOT / "data" / "phase6-step1-data-manifest.json"
STEP2_MANIFEST = ROOT / "architecture" / "phase6_step2_g0_g1_manifest.json"
STEP3_MANIFEST = ROOT / "architecture" / "phase6_step3_teacher_learning_manifest.json"


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = spec_from_loader(name, loader)
    if spec is None:
        raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec)
    sys.modules[name] = module
    loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(manifest.get("phase") == 6 and manifest.get("step") == 1, "wrong Step-1 manifest")
    require(manifest.get("engine_count") == 44 and manifest.get("new_engine_count") == 0, "Step 1 must not invent engine #45")
    guards = manifest.get("scope_guards", {})
    require(all(value is False for value in guards.values()), "Step 1 historical scope guard claims later implementation")

    require(DATA_MANIFEST.is_file(), "Step-1 data manifest missing; materializer did not run")
    data = json.loads(DATA_MANIFEST.read_text(encoding="utf-8-sig"))
    require(data.get("phase") == 6 and data.get("step") == 1, "wrong materialized data manifest")
    unicode_data = data.get("unicode", {})
    oewn_data = data.get("oewn", {})
    require(unicode_data.get("emoji_version") == "17.0", "released Unicode Emoji 17.0 authority not loaded")
    derived_emoji_count = int(unicode_data.get("rgi_count", 0))
    require(derived_emoji_count > 3000, f"Unicode RGI count unexpectedly small: {derived_emoji_count}")
    require(int(unicode_data.get("fully_qualified_count", 0)) + int(unicode_data.get("component_count", 0)) == derived_emoji_count, "Unicode RGI component arithmetic mismatch")
    require(re.fullmatch(r"[0-9a-f]{64}", str(unicode_data.get("sha256", ""))), "Unicode source hash missing")
    require(oewn_data.get("edition") == "2025+", "Open English WordNet 2025+ authority not loaded")
    source_index_records = int(oewn_data.get("index_record_count", 0))
    require(source_index_records > 100000, f"OEWN source index unexpectedly small: {source_index_records}")
    require(re.fullmatch(r"[0-9a-f]{64}", str(oewn_data.get("archive_sha256", ""))), "OEWN archive hash missing")

    lexical = load("_p6s1_lexical", ROOT / "📚" / "📖")
    vocab = load("_p6s1_vocab", ROOT / "📚" / "📚")
    tokens = load("_p6s1_tokens", ROOT / "📚" / "🔤")
    universe = load("_p6s1_universe", ROOT / "🌐" / "🌐")
    grammar = load("_p6s1_grammar", ROOT / "🧱" / "🧱")

    resolver = lexical.resolver()
    require(resolver.emoji.version == "17.0", "lexical emoji authority version mismatch")
    require(resolver.emoji_count == derived_emoji_count, "lexical emoji count differs from materialized Unicode authority")
    require(resolver.wordnet.available, "Open English WordNet is not available to lexical resolver")
    runtime_pos_lexical_keys = resolver.wordnet.lemma_count
    require(runtime_pos_lexical_keys > 100000, f"runtime normalized WordNet lexical keys unexpectedly small: {runtime_pos_lexical_keys}")
    require(runtime_pos_lexical_keys <= source_index_records, "runtime normalized lexical keys cannot exceed raw source index records")

    vocab_snapshot = vocab.VocabularyEngine.snapshot()
    require(vocab_snapshot.official_emoji_count == derived_emoji_count, "Vocabulary count differs from Unicode authority")
    require(vocab_snapshot.emoji_version == "17.0", "Vocabulary Unicode version mismatch")
    require(vocab_snapshot.semantic_seed_count == len(vocab.SEMANTIC_BASE_SYMBOLS), "semantic seed compatibility count mismatch")
    require(vocab_snapshot.first_class_symbol_count >= derived_emoji_count, "first-class EL symbol count cannot be below official emoji count")

    universe_snapshot = universe.EmojiUniverseEngine().snapshot
    require(universe_snapshot.rgi_complete, "Emoji Universe must use official materialized RGI authority")
    require(universe_snapshot.version == "17.0", "Emoji Universe version mismatch")
    require(universe_snapshot.count == derived_emoji_count, "Emoji Universe count differs from Unicode authority")

    token_authority = tokens.ELTokenAuthority()
    token_snapshot = token_authority.snapshot()
    require(token_snapshot.emoji_version == "17.0", "token authority Unicode version mismatch")
    require(token_snapshot.official_emoji_count == derived_emoji_count, "token authority emoji count mismatch")
    require(token_snapshot.english_lemma_count > 100000, "tokenizer source corpus does not expose six-figure unique English lexical coverage")
    require(token_snapshot.english_lemma_count <= runtime_pos_lexical_keys, "unique tokenizer lexical corpus cannot exceed POS-index runtime keys")
    require(token_snapshot.wordnet_available, "tokenizer source authority cannot see WordNet")
    require(len(token_authority.atomic_emoji_tokens) == derived_emoji_count, "every official RGI emoji must have one atomic token identity")
    require(all(token_authority.is_atomic_el(item) for item in token_authority.structural_tokens), "EL structural token not atomic")
    require(set(token_authority.model_special_tokens).isdisjoint(token_authority.atomic_el_tokens), "model special token collides with EL token")
    require("<ABC_TO_EL>" in token_authority.model_special_tokens and "<EL_TO_ABC>" in token_authority.model_special_tokens, "bidirectional direction tokens missing")

    easy = ("robot", "fox", "laptop", "chair", "apple", "football", "car", "phone", "light", "lock")
    missing = tuple(word for word in easy if not resolver.is_known(word))
    require(not missing, f"easy words absent from lexical knowledge: {missing}")

    direct = {
        "robot": "🤖", "fox": "🦊", "laptop": "💻", "chair": "🪑",
        "dog": "🐕", "credit card": "💳", "toothbrush": "🪥", "fire engine": "🚒",
    }
    for surface, expected in direct.items():
        result = resolver.resolve(surface, surface)
        require(result.resolved and result.expression == expected, f"defensible direct lexical mapping failed: {surface} -> {result}")

    dog = resolver.resolve("dog", "the dog runs")
    dogs = resolver.resolve("dogs", "the dogs run")
    require(dog.resolved and dogs.resolved and dog.expression == dogs.expression, "plural morphology failed for dogs")
    require(not resolver.is_known("zxqvplmno"), "synthetic nonsense must remain outside lexical knowledge")
    scarcity = resolver.resolve("scarcity", "scarcity of food")
    require(scarcity.expression != "🚗", "substring false-positive mapped scarcity to car")
    require(grammar.ELGrammarCompositionEngine.is_canonical_expression("🦊➡️🌲"), "official emoji are not accepted as valid EL composition symbols")

    lexical_source = (ROOT / "📚" / "📖").read_text(encoding="utf-8")
    token_source = (ROOT / "📚" / "🔤").read_text(encoding="utf-8")
    vocab_source = (ROOT / "📚" / "📚").read_text(encoding="utf-8")
    renderer_source = (ROOT / "⚡" / "🎞️").read_text(encoding="utf-8")
    html_source = (ROOT / "⚡" / "🖥️").read_text(encoding="utf-8")
    launcher_source = (ROOT / "▶️.cmd").read_text(encoding="utf-8")
    for source_name, source in (("lexical", lexical_source), ("token", token_source)):
        lowered = source.lower()
        for forbidden in ("qwen2.5vl", "ollamaconnector", "forgeyconnector", "chat_internal", "generate_internal", "urllib.request"):
            require(forbidden not in lowered, f"provider coupling leaked into Step-1 {source_name} authority: {forbidden}")
    require("len(CANONICAL_SYMBOLS) !=" not in vocab_source and "len(CANONICAL_SYMBOLS) ==" not in vocab_source, "fixed-size Vocabulary invariant remains")
    require("official_emoji_count" in vocab_source and "is_valid_el_symbol" in vocab_source, "dynamic Vocabulary authority missing")
    require("🔒📚501" not in html_source, "stale public 501 count remains in UI source")
    require("🔒📚?" in html_source, "neutral vocabulary placeholder missing from UI source")
    require("query('📚')" in renderer_source and "🔒📚?" in renderer_source, "renderer does not replace neutral vocabulary placeholder dynamically")
    require("materialize-phase6-step1-knowledge.ps1" in launcher_source, "source launcher does not prepare Step-1 knowledge")

    step2_state = "ABSENT"
    if STEP2_MANIFEST.is_file():
        step2 = json.loads(STEP2_MANIFEST.read_text(encoding="utf-8"))
        require(step2.get("phase") == 6 and step2.get("step") == 2, "unrecognized later-step manifest")
        require((ROOT / "🧠" / "🤖").is_file(), "Step-2 manifest exists but model source is missing")
        step2_state = "AUTHORIZED"
    else:
        require(not (ROOT / "🧠" / "🤖").exists(), "Step-2 Forgey Insta model leaked into Step 1")

    step3_state = "ABSENT"
    if STEP3_MANIFEST.is_file():
        step3 = json.loads(STEP3_MANIFEST.read_text(encoding="utf-8"))
        require(step3.get("phase") == 6 and step3.get("step") == 3, "unrecognized Step-3 manifest")
        require(step3.get("status") in {"IMPLEMENTATION_IN_PROGRESS", "PASS"}, "invalid Step-3 authorization state")
        require((ROOT / "🧑‍🏫" / "🤖").is_file(), "Step-3 manifest exists but teacher coordinator is missing")
        step3_state = "AUTHORIZED"
    else:
        require(not (ROOT / "🧑‍🏫" / "🤖").exists(), "Step-3 training coordinator leaked without authority")

    require(not (ROOT / "scripts" / "publish-phase6-release.ps1").exists(), "Step-5 release publisher leaked before Step 5")
    runtime_source = (ROOT / "↔️" / "↔️").read_text(encoding="utf-8").lower()
    require("forgeygenerationregistry" not in runtime_source and "phase6-step3" not in runtime_source, "Step-4 Forgey-first runtime routing leaked during Step 3")

    print(
        "PHASE6_STEP1_OK "
        f"emoji={derived_emoji_count} oewn_index_records={source_index_records} "
        f"runtime_pos_lexical_keys={runtime_pos_lexical_keys} tokenizer_unique_english={token_snapshot.english_lemma_count} "
        f"atomic_el={token_snapshot.atomic_el_token_count} semantic_seed={vocab_snapshot.semantic_seed_count} "
        f"public_501=ABSENT model={step2_state} teacher={step3_state} admin_runtime=ABSENT release=ABSENT"
    )


if __name__ == "__main__":
    main()
