#!/usr/bin/env python3
"""Truthful two-page Step-4 admin snapshot collector.

Missing runtime artifacts are reported as unavailable; values are never synthesized.
"""
from __future__ import annotations

from hashlib import sha256
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parent.parent


def load(name: str, path: Path):
    loader = SourceFileLoader(name, str(path)); spec = spec_from_loader(name, loader)
    if spec is None: raise RuntimeError(f"cannot load {path}")
    module = module_from_spec(spec); sys.modules[name] = module; loader.exec_module(module); return module


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''): digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path):
    try: return json.loads(path.read_text(encoding='utf-8-sig'))
    except Exception: return None


def resolve_artifact(path_value, registry_path: Path) -> Path:
    raw = Path(str(path_value or ''))
    if raw.is_absolute(): return raw
    candidates = [ROOT / raw, registry_path.parent / raw, Path.cwd() / raw]
    for candidate in candidates:
        if candidate.is_file(): return candidate.resolve()
    return (ROOT / raw).resolve()


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument('--registry', default=os.environ.get('EL_FORGEY_REGISTRY', '')); parser.add_argument('--validate', action='store_true'); args = parser.parse_args()
    registry_path = Path(args.registry).resolve() if str(args.registry).strip() else (ROOT / 'data' / 'phase6-step3' / 'generation-registry.json')
    output = {
        'schema_version': 2, 'phase': 6, 'step': 4, 'available': True,
        'registry': {'path': str(registry_path), 'available': registry_path.is_file(), 'selected_generation': None, 'generation_count': 0, 'hashes_verified': False, 'generations': [], 'history': [], 'selected_metrics': None},
        'model': {'loadable': None, 'trainable_parameters': None, 'total_parameters': None, 'vocabulary_size': None, 'model_file_bytes': None, 'tokenizer_file_bytes': None, 'vision_enabled': None, 'vision_parameters': None, 'vision_image_size': None, 'vision_patch_size': None, 'visual_tokens': None},
        'architecture': {}, 'teacher': {}, 'learning': {}, 'training': {}, 'training_proof': None, 'promotion': None,
        'diagnostics': {'available': False, 'passed': None, 'count': None}, 'knowledge': {},
    }

    step1 = read_json(ROOT / 'data' / 'phase6-step1-data-manifest.json'); step2 = read_json(ROOT / 'architecture' / 'phase6_step2_g0_g1_manifest.json'); step3 = read_json(ROOT / 'architecture' / 'phase6_step3_teacher_learning_manifest.json')
    output['knowledge'] = {'step1_available': bool(step1), 'step2_status': step2.get('status') if step2 else None, 'step3_status': step3.get('status') if step3 else None, 'emoji_count': (step1 or {}).get('emoji_count'), 'oewn_index_records': (step1 or {}).get('oewn_index_records')}
    if step2:
        model_auth = dict(step2.get('model') or {})
        output['architecture'] = {
            'family': model_auth.get('family'), 'd_model': model_auth.get('d_model'), 'attention_heads': model_auth.get('attention_heads'),
            'encoder_layers': model_auth.get('encoder_layers'), 'decoder_layers': model_auth.get('decoder_layers'), 'feed_forward': model_auth.get('feed_forward'),
            'max_context': model_auth.get('max_context'), 'pretrained_semantic_weights': model_auth.get('pretrained_semantic_weights'),
            'modalities': model_auth.get('modalities'), 'vision_image_size': model_auth.get('vision_image_size'), 'vision_patch_size': model_auth.get('vision_patch_size'),
        }

    registry = read_json(registry_path) if registry_path.is_file() else None; selected_record = None
    if registry:
        selected = str(registry.get('production_generation') or ''); generations = dict(registry.get('generations') or {}); selected_record = dict(generations.get(selected) or {})
        output['registry'].update({'selected_generation': selected or None, 'generation_count': len(generations), 'history': list(registry.get('history') or []), 'selected_metrics': selected_record.get('metrics')})
        records = []
        for generation_id, record in generations.items():
            item = dict(record); model_path = resolve_artifact(item.get('model_path'), registry_path); tokenizer_path = resolve_artifact(item.get('tokenizer_path'), registry_path)
            records.append({'generation_id': generation_id, 'parent_generation': item.get('parent_generation'), 'status': item.get('status'), 'model_sha256': item.get('model_sha256'), 'tokenizer_sha256': item.get('tokenizer_sha256'), 'model_file_bytes': model_path.stat().st_size if model_path.is_file() else None, 'tokenizer_file_bytes': tokenizer_path.stat().st_size if tokenizer_path.is_file() else None})
        output['registry']['generations'] = records
        if selected_record:
            model_path = resolve_artifact(selected_record.get('model_path'), registry_path); tokenizer_path = resolve_artifact(selected_record.get('tokenizer_path'), registry_path)
            hashes = model_path.is_file() and tokenizer_path.is_file() and file_sha256(model_path) == selected_record.get('model_sha256') and file_sha256(tokenizer_path) == selected_record.get('tokenizer_sha256')
            output['registry'].update({'hashes_verified': bool(hashes), 'model_sha256': selected_record.get('model_sha256'), 'tokenizer_sha256': selected_record.get('tokenizer_sha256')})
            output['model']['model_file_bytes'] = model_path.stat().st_size if model_path.is_file() else None; output['model']['tokenizer_file_bytes'] = tokenizer_path.stat().st_size if tokenizer_path.is_file() else None
            metrics = dict(selected_record.get('metrics') or {})
            output['training'] = {
                'teacher_probe_exact': metrics.get('teacher_probe_exact'), 'teacher_probe_total': metrics.get('teacher_probe_total'), 'teacher_token_loss': metrics.get('teacher_token_loss'),
                'frozen_benchmark_loss': metrics.get('frozen_benchmark_loss'), 'protected_probes': f"{metrics.get('protected_probe_exact')}/{metrics.get('protected_probe_total')}" if metrics.get('protected_probe_total') is not None else None,
                'roundtrip': f"{metrics.get('roundtrip_exact')}/{metrics.get('roundtrip_total')}" if metrics.get('roundtrip_total') is not None else None,
                'vision_probes': f"{metrics.get('vision_probe_exact')}/{metrics.get('vision_probe_total')}" if metrics.get('vision_probe_total') is not None else None,
                'vision_validation_pass': metrics.get('vision_validation_pass'), 'adversarial_integrity_pass': metrics.get('adversarial_integrity_pass'), 'validation_pass': metrics.get('validation_pass'),
            }
            try:
                tokenizer_module = load('_el_step4_status_tokenizer', ROOT / '📚' / '✂️'); model_module = load('_el_step4_status_model', ROOT / '🧠' / '🤖')
                tokenizer = tokenizer_module.ForgeyInstaTokenizer.load(tokenizer_path); model, metadata = model_module.ForgeyInstaTransformer.load_checkpoint(model_path, map_location='cpu'); report = model.parameter_report(); config = model.config
                output['model'].update({'loadable': True, 'trainable_parameters': int(report.trainable_parameters), 'total_parameters': int(report.total_parameters), 'vocabulary_size': int(tokenizer.vocab_size), 'metadata': metadata, 'vision_enabled': bool(config.vision_enabled), 'vision_parameters': int(report.vision_parameters), 'vision_image_size': int(config.vision_image_size), 'vision_patch_size': int(config.vision_patch_size), 'visual_tokens': int(config.visual_token_count) if config.vision_enabled else 0})
                output['architecture'].update({'modalities': ['text', 'image'] if config.vision_enabled else ['text'], 'vision_image_size': int(config.vision_image_size) if config.vision_enabled else None, 'vision_patch_size': int(config.vision_patch_size) if config.vision_enabled else None, 'visual_tokens': int(config.visual_token_count) if config.vision_enabled else 0})
            except Exception as error: output['model'].update({'loadable': False, 'load_error': type(error).__name__})
    else:
        output['available'] = False; output['reason'] = 'generation-registry-unavailable'

    evidence_dir = registry_path.parent; teacher = read_json(evidence_dir / 'teacher-evidence.json')
    output['teacher'] = {'provider': (teacher or {}).get('provider') or ((teacher or {}).get('lessons') or [{}])[0].get('provider') if teacher else None, 'model': ((teacher or {}).get('lessons') or [{}])[0].get('model') if teacher else None, 'calls': (teacher or {}).get('provider_calls'), 'admitted': (teacher or {}).get('accepted_count'), 'rejected': (teacher or {}).get('rejected_count'), 'provider_authored_el_truth': (teacher or {}).get('provider_authored_el_count'), 'self_output_truth': (teacher or {}).get('unverified_self_output_truth_count')}
    learning = read_json(evidence_dir / 'learning-v1.json'); replay = read_json(evidence_dir / 'teacher-replay.json')
    output['learning'] = {'claim_count': len((learning or {}).get('claims') or {}), 'episode_count': len((learning or {}).get('episodes') or []), 'replay_examples': len((replay or {}).get('examples') or []), 'replay_fingerprint': (replay or {}).get('fingerprint_sha256')}
    output['training_proof'] = read_json(evidence_dir / 'g2-training-proof.json'); output['promotion'] = read_json(evidence_dir / 'promotion-proof.json')
    try:
        diagnostics_module = load('_el_step4_status_diag', ROOT / '🧪' / '🧪'); report = diagnostics_module.DiagnosticsEngine().run(); output['diagnostics'] = {'available': True, 'passed': bool(report.passed), 'count': len(report.checks), 'render': report.render_el()}
    except Exception as error: output['diagnostics'] = {'available': False, 'passed': None, 'count': None, 'error': type(error).__name__}
    if args.validate: output['validation'] = {'registry_hashes': output['registry']['hashes_verified'], 'model_loadable': output['model']['loadable'], 'native_vision': output['model']['vision_enabled'] is True, 'diagnostics_passed': output['diagnostics']['passed']}
    print(json.dumps(output, ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__': main()
