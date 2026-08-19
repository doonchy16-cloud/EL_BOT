#!/usr/bin/env python3
"""Materialize a relocatable Phase-6 Forgey runtime for Windows packaging.

The training registry stores absolute build-machine paths. This step copies every
verified/production generation artifact under data/phase6-step3/runtime and
rewrites registry paths relative to the application root. Hashes and generation
semantics are preserved; no model bytes are changed.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import argparse
import json
import os
import shutil

ROOT = Path(__file__).resolve().parent.parent


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(path: Path, fallback: str) -> str:
    suffix = path.suffix if path.suffix else ""
    return fallback + suffix


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default=str(ROOT / "data" / "phase6-step3" / "generation-registry.json"))
    parser.add_argument("--manifest", default=str(ROOT / "data" / "phase6-step3" / "runtime-package-manifest.json"))
    args = parser.parse_args()

    registry_path = Path(args.registry).resolve()
    if not registry_path.is_file():
        raise FileNotFoundError("Phase-6 generation registry missing")
    payload = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    if payload.get("schema_version") != 1:
        raise RuntimeError("unsupported generation registry")
    generations = dict(payload.get("generations") or {})
    selected = str(payload.get("production_generation") or "")
    if selected != "G2" or selected not in generations:
        raise RuntimeError(f"expected selected production G2, got {selected!r}")

    runtime_root = registry_path.parent / "runtime"
    if runtime_root.exists():
        shutil.rmtree(runtime_root)
    runtime_root.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for generation_id, raw_record in generations.items():
        record = dict(raw_record)
        if record.get("status") not in {"verified", "production"}:
            raise RuntimeError(f"generation {generation_id} is not package-eligible: {record.get('status')}")
        source_model = Path(str(record.get("model_path") or "")).resolve()
        source_tokenizer = Path(str(record.get("tokenizer_path") or "")).resolve()
        if not source_model.is_file() or not source_tokenizer.is_file():
            raise FileNotFoundError(f"generation {generation_id} artifact missing")
        if digest(source_model) != str(record.get("model_sha256") or ""):
            raise RuntimeError(f"generation {generation_id} model hash mismatch before packaging")
        if digest(source_tokenizer) != str(record.get("tokenizer_sha256") or ""):
            raise RuntimeError(f"generation {generation_id} tokenizer hash mismatch before packaging")

        destination = runtime_root / generation_id
        destination.mkdir(parents=True, exist_ok=True)
        model_target = destination / safe_name(source_model, "model")
        tokenizer_target = destination / safe_name(source_tokenizer, "tokenizer")
        shutil.copy2(source_model, model_target)
        shutil.copy2(source_tokenizer, tokenizer_target)
        if digest(model_target) != record["model_sha256"] or digest(tokenizer_target) != record["tokenizer_sha256"]:
            raise RuntimeError(f"generation {generation_id} copy hash mismatch")

        model_relative = model_target.relative_to(ROOT).as_posix()
        tokenizer_relative = tokenizer_target.relative_to(ROOT).as_posix()
        record["model_path"] = model_relative
        record["tokenizer_path"] = tokenizer_relative
        payload["generations"][generation_id] = record
        manifest_rows.append({
            "generation_id": generation_id,
            "status": record.get("status"),
            "model_path": model_relative,
            "model_bytes": model_target.stat().st_size,
            "model_sha256": record["model_sha256"],
            "tokenizer_path": tokenizer_relative,
            "tokenizer_bytes": tokenizer_target.stat().st_size,
            "tokenizer_sha256": record["tokenizer_sha256"],
        })

    temporary = registry_path.with_name(registry_path.name + ".package.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, registry_path)

    manifest = {
        "schema_version": 1,
        "phase": 6,
        "step": 5,
        "status": "PORTABLE_RUNTIME_MATERIALIZED",
        "selected_generation": selected,
        "generation_count": len(manifest_rows),
        "relative_to_application_root": True,
        "registry_path": registry_path.relative_to(ROOT).as_posix(),
        "registry_sha256": digest(registry_path),
        "generations": manifest_rows,
    }
    manifest_path = Path(args.manifest).resolve()
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PHASE6_STEP5_RUNTIME_OK selected={selected} generations={len(manifest_rows)} registry={manifest['registry_sha256'][:12]}")


if __name__ == "__main__":
    main()
