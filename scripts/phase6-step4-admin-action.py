#!/usr/bin/env python3
"""High-friction Step-4 model administration actions.

Authentication/confirmation happens in Electron main process. This helper performs
only deterministic registry mutations and emits no secrets.
"""
from __future__ import annotations
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path
import argparse, json, sys

ROOT = Path(__file__).resolve().parent.parent

def load(path: Path):
    loader=SourceFileLoader('_el_step4_admin_registry',str(path));spec=spec_from_loader('_el_step4_admin_registry',loader)
    if spec is None: raise RuntimeError('registry module unavailable')
    module=module_from_spec(spec);sys.modules['_el_step4_admin_registry']=module;loader.exec_module(module);return module

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--registry',required=True);sub=parser.add_subparsers(dest='action',required=True);rb=sub.add_parser('rollback');rb.add_argument('generation');args=parser.parse_args()
    module=load(ROOT/'🗃️'/'🤖');registry=module.ForgeyGenerationRegistry(Path(args.registry))
    if args.action=='rollback':
        before=registry.production_generation;record=registry.rollback(args.generation)
        if not registry.verify_generation_hashes(args.generation): raise RuntimeError('post-rollback hash verification failed')
        print(json.dumps({'ok':True,'action':'rollback','previous_generation':before,'selected_generation':registry.production_generation,'model_sha256':record['model_sha256']},separators=(',',':')))

if __name__=='__main__': main()
