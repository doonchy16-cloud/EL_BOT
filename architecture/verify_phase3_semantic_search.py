#!/usr/bin/env python3
"""Phase 3 deterministic semantic-search and translation-intelligence gate."""
from __future__ import annotations

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import json
import sys
import unicodedata

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "architecture" / "phase3_semantic_search_manifest.json"


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
    require(manifest["phase"] == 3, "wrong Phase-3 manifest")
    require(manifest["status"] == "PASS", "Phase-3 authority must remain PASS")
    require(manifest["source_present_target_engines"] == 39, "source-present target must be 39")
    require(manifest["planned_only_target_engines"] == 5, "planned-only target must be 5")
    require(manifest["canonical_vocabulary_count"] == 501, "501 authority changed")
    require(len(manifest["implemented"]) == 9, "Phase 3 must implement nine engines")

    forbidden = ("OllamaConnector", "qwen2.5vl", "ForgeyConnector", "chat_internal", "generate_internal")
    for item in manifest["implemented"]:
        path = ROOT / item["source_path"]
        require(path.is_file(), f"missing Phase-3 source: {path}")
        source = path.read_text(encoding="utf-8")
        for token in forbidden:
            require(token not in source, f"provider coupling in {item['id']}: {token}")
    bridge_source = (ROOT / "🔤➡️😀" / "🧠").read_text(encoding="utf-8")
    for token in forbidden:
        require(token not in bridge_source, f"provider coupling in Phase-3 bridge: {token}")

    vocab = load("_p3_vocab", ROOT / "📚" / "📚")
    universe = load("_p3_universe", ROOT / "🌐" / "🌐")
    context = load("_p3_context", ROOT / "🧭" / "🧭")
    decomp = load("_p3_decomp", ROOT / "🧩" / "🧩")
    graph = load("_p3_graph", ROOT / "🗺️" / "🗺️")
    grammar = load("_p3_grammar", ROOT / "🧱" / "🧱")
    frontier = load("_p3_frontier", ROOT / "♾️" / "♾️")
    search = load("_p3_search", ROOT / "🔍" / "🔍")
    competition = load("_p3_competition", ROOT / "🏆" / "🏆")
    experiment = load("_p3_experiment", ROOT / "🧫" / "🧫")
    counter = load("_p3_counter", ROOT / "🪤" / "🪤")
    abc = load("_p3_abc", ROOT / "🔤➡️😀" / "🔤➡️😀")
    emoji = load("_p3_emoji", ROOT / "😀➡️🔤" / "😀➡️🔤")

    require(len(vocab.CANONICAL_SYMBOLS) == 501 and len(set(vocab.CANONICAL_SYMBOLS)) == 501, "canonical 501 invariant changed")

    ctx = context.ContextSenseDisambiguationEngine()
    require(ctx.resolve("converter", "Use the converter.").sense_id == "conversion-tool", "converter sense failed")
    require(ctx.resolve("ChatGPT", "ChatGPT answered me.").sense_id == "chatgpt-assistant", "ChatGPT sense failed")
    require(ctx.resolve("words", "These words form a sentence.").sense_id == "language-word", "words language sense failed")
    product = ctx.resolve("Word", "Microsoft Word edits a DOCX document.")
    require(product.sense_id == "microsoft-word-product" and product.ambiguous, "Word product disambiguation failed")

    graph_engine = graph.SemanticGraphEngine()
    require("transform-action" in graph_engine.expand("conversion-tool", depth=1), "semantic graph conversion edge missing")
    require("conversation" in graph_engine.expand("chatgpt-assistant", depth=1), "semantic graph ChatGPT edge missing")

    de = decomp.ConceptDecompositionEngine()
    converter = de.decompose("converter", "Use the converter.")
    chatgpt = de.decompose("ChatGPT", "ChatGPT answered.")
    words = de.decompose("words", "These words matter.")
    require(converter.resolved and {"input", "transform-action", "output"}.issubset(set(converter.concept_keys)), "converter decomposition failed")
    require(chatgpt.resolved and {"ai", "conversation"}.issubset(set(chatgpt.concept_keys)), "ChatGPT decomposition failed")
    require(words.resolved and "text-unit" in words.concept_keys, "words decomposition failed")

    composer = grammar.ELGrammarCompositionEngine()
    converter_template = composer.compose_primary(converter)
    chatgpt_template = composer.compose_primary(chatgpt)
    words_template = composer.compose_primary(words)
    require(converter_template is not None and converter_template.expression == "📥➡️🔄➡️📤" and converter_template.canonical, "converter grammar failed")
    require(chatgpt_template is not None and "🤖" in chatgpt_template.expression and "💬" in chatgpt_template.expression and chatgpt_template.canonical, "ChatGPT grammar failed")
    require(words_template is not None and words_template.expression == "🔤" and words_template.canonical, "words grammar failed")

    frontiers = frontier.SearchFrontierExhaustionEngine()
    toy = frontiers.define(units=("😀", "🔥", "🚀"), min_length=1, max_length=2, frontier_id="toy-3x2")
    require(toy.total_candidates == 12, "3-unit depth-2 frontier must contain 3 + 9 = 12 candidates")
    require(frontiers.candidate_at(toy, 0) == "😀" and frontiers.candidate_at(toy, 3) == "😀😀" and frontiers.candidate_at(toy, 11) == "🚀🚀", "frontier coordinate mapping failed")

    complete = search.CompleteCandidateSearchEngine()
    partial, toy_partial = complete.search(toy, lambda candidate, index: {"score": float(index), "valid": True}, limit=4)
    require(partial.evaluated_count == 4 and not partial.exhausted and toy_partial.cursor == 4, "partial frontier checkpoint failed")
    checkpoint = frontiers.checkpoint(toy_partial)
    resumed = frontiers.resume(checkpoint)
    rest, toy_done, toy_proof = complete.search_to_exhaustion(resumed, lambda candidate, index: {"score": float(index), "valid": True})
    require(rest.evaluated_count == 8 and toy_done.cursor == 12 and toy_proof.exhausted and toy_proof.visited_candidates == 12, "toy frontier exhaustion proof failed")

    u = universe.EmojiUniverseEngine()
    full = frontiers.define(units=u.units, min_length=1, max_length=1, frontier_id="full-universe-depth1-gate")
    full_result, full_done, full_proof = complete.search_to_exhaustion(
        full,
        lambda candidate, index: {"score": 1.0 if candidate in vocab.CANONICAL_SYMBOLS else 0.0, "valid": candidate in vocab.CANONICAL_SYMBOLS, "canonical": candidate in vocab.CANONICAL_SYMBOLS},
    )
    require(full.total_candidates == u.snapshot.count, "full depth-1 frontier must equal loaded universe count")
    require(full_result.evaluated_count == u.snapshot.count and full_done.cursor == u.snapshot.count and full_proof.exhausted, "full depth-1 universe was not exhausted")
    require(len(full_result.survivors) == 501, "full-universe canonical survivor count must preserve 501")

    outside_501 = next((unit for unit in u.units if unit not in vocab.CANONICAL_SYMBOLS and any(unicodedata.category(ch) == "So" and unicodedata.name(ch, "") for ch in unit)), None)
    require(outside_501 is not None, "no investigable non-501 emoji available for reverse test")
    reverse = emoji.EmojiToABCEngine().translate(outside_501, cross_verify=False, emit=False)
    require(reverse.winner.startswith("The emoji represents "), f"non-501 reverse identity not selected: {outside_501} -> {reverse.winner}")
    require(reverse.metrics.get("investigable_noncanonical") == 1 and reverse.metrics.get("unknown") == 0, "non-501 reverse classification failed")
    require(reverse.metrics.get("quality_status") == "hold", "noncanonical identity must remain HOLD until canonical graduation")

    ranked = competition.CandidateCompetitionEngine.compete((
        search.CandidateEvaluation(0, "🔥", 2.0, True, ("low",), (), True),
        search.CandidateEvaluation(1, "🚀", 9.0, True, ("high",), (), True),
        search.CandidateEvaluation(2, "❓", 99.0, False, ("invalid",), (), True),
    ))
    require(ranked.winner is not None and ranked.winner.candidate == "🚀" and len(ranked.ranked) == 2, "candidate competition failed")

    experiments = experiment.ExperimentEngine()
    word_report = experiments.run("word", (
        ("These words are useful in a sentence.", "language-word"),
        ("Microsoft Word opened the document editor.", "microsoft-word-product"),
    ))
    require(word_report.passed and word_report.pass_rate == 1.0, "context experiment failed")

    traps = counter.CounterexampleAdversarialSemanticsEngine()
    word_trap = traps.challenge("word", "language-word")
    converter_trap = traps.challenge("converter", "conversion-tool")
    require(word_trap.tested == 2 and len(word_trap.counterexamples) == 1 and not word_trap.passed, "Word counterexample detection failed")
    require(converter_trap.passed and converter_trap.tested == 2, "converter adversarial contexts failed")

    engine = abc.ABCToEmojiEngine()
    for source in ("converter", "ChatGPT", "words"):
        result = engine.translate(source, cross_verify=False, emit=False)
        require(result.winner and result.winner != "🟡❓" and "❓" not in result.winner, f"Phase-3 normal-word rescue failed: {source} -> {result.winner}")
        require(result.metrics.get("quality_status") != "fail", f"Phase-3 target still FAIL: {source} {result.metrics}")
        require(int(result.metrics.get("phase3_resolved_unknowns", 0)) >= 1, f"Phase-3 resolver not used for {source}")
        require(result.metrics.get("phase3_search_exhausted") is True, f"full universe search not exhausted for {source}")
        require(int(result.metrics.get("phase3_search_evaluated", 0)) == int(result.metrics.get("phase3_search_frontier_total", -1)), f"search coordinate count mismatch for {source}")

    nonsense = engine.translate("flibbertigibbet", cross_verify=False, emit=False)
    require(nonsense.metrics.get("quality_status") == "fail" and "❓" in nonsense.winner, "genuine unresolved nonsense must remain FAIL")

    combined = engine.translate("Use the converter for words with ChatGPT.", cross_verify=False, emit=False)
    require(combined.metrics.get("quality_status") != "fail" and int(combined.metrics.get("phase3_resolved_unknowns", 0)) >= 3, "combined Phase-3 semantic rescue failed")

    print("✅🧠🔍3️⃣ 🧭✅ 🧩✅ 🗺️✅ 🧱✅ ♾️12/12✅ 🌐" + str(u.snapshot.count) + "/" + str(u.snapshot.count) + "✅ 🔍✅ 🏆✅ 🧫✅ 🪤✅ 🔤3/3✅ 😀🌐✅ 🤖❌")


if __name__ == "__main__":
    main()
