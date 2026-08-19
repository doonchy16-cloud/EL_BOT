#!/usr/bin/env python3
"""Prove multimodal Forgey G2 from the built Windows package, not source runtime."""
from __future__ import annotations

from pathlib import Path
import argparse
import json
import os
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str], *, cwd: Path, env: dict[str, str], stdin: str | None = None, timeout: int = 240) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command,cwd=str(cwd),env=env,input=stdin,text=True,encoding="utf-8",errors="replace",stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=timeout,check=False)
    if result.returncode != 0: raise RuntimeError(f"command failed {result.returncode}: {result.stderr[-1600:]}")
    return result


def parse_one_json(stdout: str) -> dict:
    text = stdout.strip()
    if not text.startswith("{") or not text.endswith("}"): raise RuntimeError(f"expected one JSON object, got: {text[:400]!r}")
    return json.loads(text)


def main() -> None:
    parser = argparse.ArgumentParser();parser.add_argument("--app-root", default=str(ROOT / "dist" / "win-unpacked" / "resources" / "app"));parser.add_argument("--output", default=str(ROOT / "dist" / "phase6-package-forgey-proof.json"));args = parser.parse_args()
    app_root = Path(args.app_root).resolve();packaged_python = app_root / "python" / "python.exe";runtime = app_root / (chr(0x2194) + chr(0xFE0F)) / chr(0x26A1);registry = app_root / "data" / "phase6-step3" / "generation-registry.json";status_script = app_root / "scripts" / "phase6-step4-status.py";vision_script = app_root / "scripts" / "phase6-vision-infer.py";admin_script = app_root / "scripts" / "phase6-step4-admin-action.py";architecture_manifest = app_root / "architecture" / "phase6_step4_runtime_console_manifest.json"
    required = [packaged_python,runtime,registry,status_script,vision_script,admin_script,architecture_manifest,app_root/"🧠"/"🤖",app_root/"🧠"/"👁️"]
    missing=[str(path) for path in required if not path.is_file()]
    if missing: raise FileNotFoundError("packaged Phase-6 runtime files missing: " + ", ".join(missing))
    env=dict(os.environ);env.pop("EL_PYTHON",None);env["PYTHONIOENCODING"]="utf-8";env["EL_FORGEY_REGISTRY"]=str(registry)
    torch=run([str(packaged_python),"-c","import sys,torch;assert sys.version_info[:2]==(3,12);assert torch.__version__.startswith('2.13.0');print(torch.__version__)"],cwd=app_root,env=env,timeout=30).stdout.strip()

    forward=parse_one_json(run([str(packaged_python),str(runtime),chr(0x1F500)],cwd=app_root,env=env,stdin="2\nvehicle powered by pedals with two wheels").stdout);bicycle=chr(0x1F6B2)
    reverse=parse_one_json(run([str(packaged_python),str(runtime),chr(0x1F500)],cwd=app_root,env=env,stdin="1\n"+bicycle).stdout)
    fm=dict(forward.get("metrics") or {});rm=dict(reverse.get("metrics") or {})
    if forward.get("winner")!=bicycle: raise AssertionError(f"packaged forward mismatch: {forward.get('winner')!r}")
    if str(reverse.get("winner") or "").strip().rstrip(".!?").casefold()!="bicycle": raise AssertionError(f"packaged reverse mismatch: {reverse.get('winner')!r}")
    for metrics in (fm,rm):
        if metrics.get("forgey_primary_released") is not True or metrics.get("forgey_generation")!="G2": raise AssertionError("packaged Forgey primary/G2 proof failed")
        if int(metrics.get("provider_calls",-1))!=0 or float(metrics.get("roundtrip",0) or 0)!=1.0: raise AssertionError("packaged text inference provider/roundtrip proof failed")

    vision_el_path=ROOT/"dist"/"phase6-package-vision-el.json";vision_abc_path=ROOT/"dist"/"phase6-package-vision-abc.json";red=chr(0x1F534)
    run([str(packaged_python),str(vision_script),"--registry",str(registry),"--direction","IMAGE_TO_EL","--fixture-concept","red-circle","--fixture-seed","9000","--expected",red,"--evidence",str(vision_el_path)],cwd=app_root,env=env,timeout=90)
    run([str(packaged_python),str(vision_script),"--registry",str(registry),"--direction","IMAGE_TO_ABC","--fixture-concept","red-circle","--fixture-seed","9000","--expected","red circle","--evidence",str(vision_abc_path)],cwd=app_root,env=env,timeout=90)
    vision_el=json.loads(vision_el_path.read_text(encoding="utf-8"));vision_abc=json.loads(vision_abc_path.read_text(encoding="utf-8"))
    for evidence,direction in ((vision_el,"IMAGE_TO_EL"),(vision_abc,"IMAGE_TO_ABC")):
        if evidence.get("generation")!="G2" or evidence.get("direction")!=direction or evidence.get("exact") is not True: raise AssertionError("packaged native vision exactness failed")
        if evidence.get("vision_enabled") is not True or int(evidence.get("vision_parameters",0))<=0: raise AssertionError("packaged native vision graph missing")
        if int(evidence.get("provider_calls",-1))!=0: raise AssertionError("packaged native vision called provider")

    status=parse_one_json(run([str(packaged_python),str(status_script),"--registry",str(registry),"--validate"],cwd=app_root,env=env,timeout=60).stdout);reg=dict(status.get("registry") or {});model=dict(status.get("model") or {});diagnostics=dict(status.get("diagnostics") or {});training=dict(status.get("training") or {})
    if reg.get("selected_generation")!="G2" or reg.get("hashes_verified") is not True: raise AssertionError("packaged registry/hash proof failed")
    params=int(model.get("trainable_parameters") or 0);vision_params=int(model.get("vision_parameters") or 0)
    if model.get("loadable") is not True or not (1000000<=params<=3000000): raise AssertionError("packaged model load/parameter proof failed")
    if model.get("vision_enabled") is not True or vision_params<=0 or int(model.get("vision_image_size") or 0)!=64 or int(model.get("vision_patch_size") or 0)!=8: raise AssertionError("packaged native vision status proof failed")
    if training.get("vision_validation_pass") is not True: raise AssertionError("packaged selected generation lacks native-vision promotion proof")
    if int(model.get("model_file_bytes") or 0)<=0 or int(model.get("tokenizer_file_bytes") or 0)<=0: raise AssertionError("packaged model/tokenizer size proof failed")
    if diagnostics.get("passed") is not True or int(diagnostics.get("count") or 0)!=44: raise AssertionError("packaged diagnostics not 44/44")

    evidence={"schema_version":2,"phase":6,"step":5,"app_root":str(app_root),"embedded_python":True,"embedded_torch":torch,"registry":str(registry.relative_to(app_root)).replace("\\","/"),"selected_generation":"G2","registry_hashes_verified":True,"trainable_parameters":params,"vision_enabled":True,"vision_parameters":vision_params,"vision_image_size":int(model["vision_image_size"]),"vision_patch_size":int(model["vision_patch_size"]),"vision_probes":training.get("vision_probes"),"model_file_bytes":int(model["model_file_bytes"]),"tokenizer_file_bytes":int(model["tokenizer_file_bytes"]),"forward_winner":forward["winner"],"reverse_winner":reverse["winner"],"forward_provider_calls":int(fm["provider_calls"]),"reverse_provider_calls":int(rm["provider_calls"]),"forward_roundtrip":float(fm["roundtrip"]),"reverse_roundtrip":float(rm["roundtrip"]),"vision_image_to_el":vision_el,"vision_image_to_abc":vision_abc,"native_vision_provider_calls":int(vision_el["provider_calls"])+int(vision_abc["provider_calls"]),"diagnostics":"44/44"}
    output=Path(args.output).resolve();output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"PHASE6_STEP5_PACKAGE_FORGEY_OK selected=G2 provider=0 native_vision=PASS params={params} vision_params={vision_params} torch={torch} diagnostics=44/44")


if __name__ == "__main__": main()