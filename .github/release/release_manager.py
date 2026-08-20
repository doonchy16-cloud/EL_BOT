#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from typing import Any

VERSION = "0.6.0"
PHASE5_VERSION = "0.5.0"
PHASE5_SHA = "c489d6f79d2f21d9544d8631dda3de7793adebf0"

V06_SOURCE_ASSETS = [
    f"dist/EL-Bot-Setup-{VERSION}-x64.exe",
    f"dist/EL-Bot-Portable-{VERSION}-x64.exe",
    "dist/package-smoke.json",
    "dist/phase6-package-forgey-proof.json",
    "dist/phase6-package-vision-el.json",
    "dist/phase6-package-vision-abc.json",
    "data/phase6-step3/runtime-package-manifest.json",
    "proof/phase5/hourglass-30fps.mp4",
    "proof/phase5/hourglass-contact-sheet.png",
    "proof/phase5/ui-idle.png",
    "proof/phase5/ui-warning.png",
    "proof/phase5/preview-zoom.png",
    "proof/phase5/proof.json",
]
V06_MANIFEST = "dist/phase6-release-manifest.json"

V05_SOURCE_ASSETS = [
    "dist/EL-Bot-Setup-0.5.0-x64.exe",
    "dist/EL-Bot-Portable-0.5.0-x64.exe",
    "dist/package-smoke.json",
    "proof/phase5/hourglass-30fps.mp4",
    "proof/phase5/hourglass-contact-sheet.png",
    "proof/phase5/ui-idle.png",
    "proof/phase5/ui-warning.png",
    "proof/phase5/preview-zoom.png",
    "proof/phase5/proof.json",
]
V05_MANIFEST = "dist/phase5-release-manifest.json"

REQUIRED_V05_CORE = {
    "EL-Bot-Setup-0.5.0-x64.exe",
    "EL-Bot-Portable-0.5.0-x64.exe",
    "package-smoke.json",
}
RELEASE_API_VERSION = "2022-11-28"


class ReleaseError(RuntimeError):
    pass


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    print(message, flush=True)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseError(message)


def env_required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ReleaseError(f"{name} missing")
    return value


REPO = env_required("GITHUB_REPOSITORY")
TOKEN = env_required("GITHUB_TOKEN")
TARGET_SHA = env_required("GITHUB_SHA")
require(len(TARGET_SHA) == 40, f"GITHUB_SHA must be full 40-character SHA, got {TARGET_SHA!r}")
API = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
WORKSPACE = pathlib.Path(os.environ.get("GITHUB_WORKSPACE", os.getcwd())).resolve()
RUNNER_TEMP = pathlib.Path(env_required("RUNNER_TEMP")).resolve()
TOOL_CACHE = pathlib.Path(env_required("RUNNER_TOOL_CACHE")).resolve()
STATE_PATH = pathlib.Path(
    os.environ.get("EL_RELEASE_STATE", str(RUNNER_TEMP / "el-bot-release-state.json"))
).resolve()
CACHE_ROOT = TOOL_CACHE / "ELReleaseCheckpoint"
V06_TAG = f"el-bot-v{VERSION}-{TARGET_SHA[:12]}"
V05_TAG = f"el-bot-v{PHASE5_VERSION}-{PHASE5_SHA[:12]}"


def state_load() -> dict[str, Any]:
    if STATE_PATH.exists():
        with STATE_PATH.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def state_save(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(state, handle, indent=2, sort_keys=True)
        handle.write("\n")
    tmp.replace(STATE_PATH)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: pathlib.Path, root: pathlib.Path = WORKSPACE) -> dict[str, Any]:
    rel = path.relative_to(root).as_posix()
    return {
        "path": rel,
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def json_read(path: pathlib.Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def json_write(path: pathlib.Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def safe_response_body(error: urllib.error.HTTPError) -> str:
    try:
        raw = error.read(4096)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def api_request(
    method: str,
    path_or_url: str,
    *,
    payload: Any | None = None,
    expected: set[int] | None = None,
    attempts: int = 6,
) -> Any:
    expected = expected or {200, 201, 202, 204}
    url = path_or_url if path_or_url.startswith("http") else f"{API}{path_or_url}"
    body = None
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": RELEASE_API_VERSION,
        "User-Agent": "EL-Bot-Release-Manager",
    }
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                status = int(response.status)
                data = response.read()
            if status not in expected:
                raise ReleaseError(f"GitHub API {method} {url} returned HTTP {status}")
            if not data:
                return None
            return json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in expected:
                return None
            last_error = exc
            if exc.code in {400, 401, 403, 404, 409, 422}:
                raise
            if attempt == attempts:
                break
            delay = min(30, 3 * attempt)
            log(
                f"API_RETRY method={method} status={exc.code} attempt={attempt}/{attempts} "
                f"delay={delay}s url={url}"
            )
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            delay = min(30, 3 * attempt)
            log(
                f"API_RETRY method={method} network={type(exc).__name__} "
                f"attempt={attempt}/{attempts} delay={delay}s url={url}"
            )
            time.sleep(delay)

    if isinstance(last_error, urllib.error.HTTPError):
        body_text = safe_response_body(last_error)
        raise ReleaseError(
            f"GitHub API failed after {attempts} attempts: {method} {url} "
            f"HTTP {last_error.code} {body_text[:1000]}"
        ) from last_error
    raise ReleaseError(
        f"GitHub API failed after {attempts} attempts: {method} {url}: {last_error}"
    ) from last_error


def api_optional_get(path: str) -> Any | None:
    try:
        return api_request("GET", path)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise ReleaseError(
            f"GitHub API GET {path} failed HTTP {exc.code}: {safe_response_body(exc)[:1000]}"
        ) from exc


def paged_get(path: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    page = 1
    separator = "&" if "?" in path else "?"
    while True:
        batch = api_request("GET", f"{path}{separator}per_page=100&page={page}")
        require(isinstance(batch, list), f"Expected list from GitHub API: {path}")
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return results


def list_releases() -> list[dict[str, Any]]:
    return paged_get(f"/repos/{REPO}/releases")


def list_assets(release_id: int) -> list[dict[str, Any]]:
    return paged_get(f"/repos/{REPO}/releases/{release_id}/assets")


def list_branches() -> list[dict[str, Any]]:
    return paged_get(f"/repos/{REPO}/branches")


def get_release_by_tag(tag: str) -> dict[str, Any] | None:
    encoded = urllib.parse.quote(tag, safe="")
    result = api_optional_get(f"/repos/{REPO}/releases/tags/{encoded}")
    if result is None:
        return None
    require(isinstance(result, dict), f"Release-by-tag response is not an object: {tag}")
    return result


def get_tag_ref(tag: str) -> dict[str, Any] | None:
    encoded = urllib.parse.quote(tag, safe="")
    result = api_optional_get(f"/repos/{REPO}/git/ref/tags/{encoded}")
    if result is None:
        return None
    require(isinstance(result, dict), f"Tag-ref response is not an object: {tag}")
    return result


def delete_tag(tag: str) -> None:
    encoded = urllib.parse.quote(tag, safe="")
    try:
        api_request(
            "DELETE",
            f"/repos/{REPO}/git/refs/tags/{encoded}",
            expected={204},
            attempts=5,
        )
        log(f"TAG_DELETE_OK tag={tag}")
    except urllib.error.HTTPError as exc:
        if exc.code in {404, 422}:
            return
        raise ReleaseError(
            f"Failed deleting tag {tag}: HTTP {exc.code} {safe_response_body(exc)[:1000]}"
        ) from exc


def delete_release(release: dict[str, Any], delete_associated_tag: bool = True) -> None:
    release_id = int(release["id"])
    tag = str(release.get("tag_name") or "")
    try:
        api_request(
            "DELETE",
            f"/repos/{REPO}/releases/{release_id}",
            expected={204},
            attempts=5,
        )
        log(f"RELEASE_DELETE_OK id={release_id} tag={tag}")
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise ReleaseError(
                f"Failed deleting release {release_id}: HTTP {exc.code} "
                f"{safe_response_body(exc)[:1000]}"
            ) from exc
    if delete_associated_tag and tag:
        delete_tag(tag)


def delete_asset(asset_id: int) -> None:
    try:
        api_request(
            "DELETE",
            f"/repos/{REPO}/releases/assets/{asset_id}",
            expected={204},
            attempts=5,
        )
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise ReleaseError(
                f"Failed deleting release asset {asset_id}: HTTP {exc.code} "
                f"{safe_response_body(exc)[:1000]}"
            ) from exc


def create_or_get_release(
    *,
    tag: str,
    target_sha: str,
    name: str,
    body: str,
) -> dict[str, Any]:
    existing = get_release_by_tag(tag)
    if existing:
        target = str(existing.get("target_commitish") or "")
        if target and target.lower() != target_sha.lower():
            log(
                f"RELEASE_RECREATE_WRONG_TARGET tag={tag} "
                f"existing_target={target} expected={target_sha}"
            )
            delete_release(existing, delete_associated_tag=True)
            existing = None
        else:
            return existing

    ref = get_tag_ref(tag)
    if ref:
        ref_sha = str(((ref.get("object") or {}).get("sha")) or "")
        if ref_sha and ref_sha.lower() != target_sha.lower():
            log(
                f"TAG_RECREATE_WRONG_TARGET tag={tag} "
                f"existing_target={ref_sha} expected={target_sha}"
            )
            delete_tag(tag)

    payload = {
        "tag_name": tag,
        "target_commitish": target_sha,
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False,
    }
    try:
        release = api_request("POST", f"/repos/{REPO}/releases", payload=payload)
    except Exception as exc:
        release = get_release_by_tag(tag)
        if release is None:
            raise ReleaseError(f"Unable to create release {tag}: {exc}") from exc
    require(isinstance(release, dict), f"Create release returned non-object for {tag}")
    log(f"RELEASE_READY id={release.get('id')} tag={tag} target={target_sha}")
    return release


def asset_remote_ok(asset: dict[str, Any], local: dict[str, Any]) -> bool:
    if str(asset.get("name") or "") != local["name"]:
        return False
    if str(asset.get("state") or "") != "uploaded":
        return False
    if int(asset.get("size") or -1) != int(local["bytes"]):
        return False
    digest = str(asset.get("digest") or "")
    if digest:
        return digest.lower() == f"sha256:{local['sha256']}".lower()
    return True


def ensure_asset(
    release: dict[str, Any],
    local_path: pathlib.Path,
    *,
    attempts: int = 6,
) -> dict[str, Any]:
    release_id = int(release["id"])
    upload_base = str(release.get("upload_url") or "").split("{", 1)[0]
    require(upload_base.startswith("http"), f"Release upload URL missing for {release_id}")
    local = {
        "name": local_path.name,
        "bytes": local_path.stat().st_size,
        "sha256": sha256_file(local_path),
    }

    for attempt in range(1, attempts + 1):
        assets = list_assets(release_id)
        matches = [a for a in assets if str(a.get("name") or "") == local["name"]]
        good = [a for a in matches if asset_remote_ok(a, local)]
        if len(good) == 1:
            for duplicate in matches:
                if int(duplicate["id"]) != int(good[0]["id"]):
                    delete_asset(int(duplicate["id"]))
            log(
                f"ASSET_PRESENT name={local['name']} bytes={local['bytes']} "
                f"sha256={local['sha256'][:12]}"
            )
            return good[0]

        for asset in matches:
            delete_asset(int(asset["id"]))

        encoded_name = urllib.parse.quote(local["name"], safe="")
        upload_url = f"{upload_base}?name={encoded_name}"
        curl_args = [
            "curl.exe",
            "--http1.1",
            "--fail-with-body",
            "--silent",
            "--show-error",
            "--location",
            "--connect-timeout",
            "30",
            "--max-time",
            "2400",
            "-X",
            "POST",
            "-H",
            f"Authorization: Bearer {TOKEN}",
            "-H",
            "Accept: application/vnd.github+json",
            "-H",
            f"X-GitHub-Api-Version: {RELEASE_API_VERSION}",
            "-H",
            "Content-Type: application/octet-stream",
            "--data-binary",
            f"@{local_path}",
            upload_url,
        ]
        completed = subprocess.run(
            curl_args,
            cwd=WORKSPACE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            log(
                f"ASSET_UPLOAD_TRANSPORT_FAIL name={local['name']} attempt={attempt}/{attempts} "
                f"curl={completed.returncode} stderr={completed.stderr[-600:].strip()!r}"
            )
        else:
            log(
                f"ASSET_UPLOAD_TRANSPORT_OK name={local['name']} attempt={attempt}/{attempts}"
            )

        time.sleep(3)
        after = list_assets(release_id)
        uploaded = [
            a
            for a in after
            if str(a.get("name") or "") == local["name"] and asset_remote_ok(a, local)
        ]
        if len(uploaded) == 1:
            log(
                f"ASSET_UPLOAD_VERIFIED name={local['name']} bytes={local['bytes']} "
                f"sha256={local['sha256'][:12]} attempt={attempt}"
            )
            return uploaded[0]

        broken = [a for a in after if str(a.get("name") or "") == local["name"]]
        for asset in broken:
            delete_asset(int(asset["id"]))

        if attempt < attempts:
            delay = min(45, 5 * attempt)
            log(
                f"ASSET_UPLOAD_RETRY name={local['name']} attempt={attempt}/{attempts} "
                f"delay={delay}s"
            )
            time.sleep(delay)

    raise ReleaseError(
        f"ASSET_UPLOAD_FAILED name={local['name']} bytes={local['bytes']} "
        f"sha256={local['sha256']}"
    )


def verify_release_target(release: dict[str, Any], tag: str, target_sha: str) -> None:
    require(str(release.get("tag_name") or "") == tag, f"Release tag mismatch: {tag}")
    require(not bool(release.get("draft")), f"Release {tag} is still draft")
    require(not bool(release.get("prerelease")), f"Release {tag} is prerelease")
    target = str(release.get("target_commitish") or "")
    require(
        target.lower() == target_sha.lower(),
        f"Release {tag} target mismatch: {target} != {target_sha}",
    )
    ref = get_tag_ref(tag)
    require(ref is not None, f"Release tag ref missing: {tag}")
    ref_obj = ref.get("object") or {}
    require(
        str(ref_obj.get("type") or "") == "commit",
        f"Release tag {tag} is not a lightweight commit ref",
    )
    require(
        str(ref_obj.get("sha") or "").lower() == target_sha.lower(),
        f"Release tag {tag} ref target mismatch",
    )


def verified_asset_inventory(
    release: dict[str, Any],
    local_files: list[pathlib.Path],
    *,
    exact: bool,
) -> list[dict[str, Any]]:
    release_id = int(release["id"])
    assets = list_assets(release_id)
    by_name: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        by_name.setdefault(str(asset.get("name") or ""), []).append(asset)

    expected_names = {p.name for p in local_files}
    for local_path in local_files:
        local = {
            "name": local_path.name,
            "bytes": local_path.stat().st_size,
            "sha256": sha256_file(local_path),
        }
        matches = by_name.get(local["name"], [])
        require(
            len(matches) == 1 and asset_remote_ok(matches[0], local),
            f"Remote release asset verification failed for {local['name']}",
        )
    if exact:
        require(
            len(assets) == len(local_files),
            f"Release {release.get('tag_name')} expected exactly {len(local_files)} assets, "
            f"found {len(assets)}",
        )
        require(
            {str(a.get("name") or "") for a in assets} == expected_names,
            f"Release {release.get('tag_name')} has unexpected asset names",
        )
    return assets


def verify_remote_records(
    release: dict[str, Any],
    records: list[dict[str, Any]],
    *,
    exact: bool,
) -> list[dict[str, Any]]:
    assets = list_assets(int(release["id"]))
    by_name: dict[str, list[dict[str, Any]]] = {}
    for asset in assets:
        by_name.setdefault(str(asset.get("name") or ""), []).append(asset)

    expected_names = {str(record["name"]) for record in records}
    for record in records:
        name = str(record["name"])
        matches = by_name.get(name, [])
        require(len(matches) == 1, f"Remote asset count mismatch for {name}")
        asset = matches[0]
        require(str(asset.get("state") or "") == "uploaded", f"Remote asset not uploaded: {name}")
        require(int(asset.get("size") or -1) == int(record["bytes"]), f"Remote asset size mismatch: {name}")
        digest = str(asset.get("digest") or "")
        if digest:
            require(
                digest.lower() == f"sha256:{record['sha256']}".lower(),
                f"Remote asset digest mismatch: {name}",
            )
    if exact:
        require(len(assets) == len(records), "Remote asset count does not match recorded release set")
        require(
            {str(asset.get("name") or "") for asset in assets} == expected_names,
            "Remote asset names do not match recorded release set",
        )
    return assets


def run(
    args: list[str],
    *,
    cwd: pathlib.Path = WORKSPACE,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess[str]:
    display = " ".join(args)
    log(f"RUN cwd={cwd} cmd={display}")
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        errors="replace",
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
        timeout=timeout,
    )
    if completed.returncode != 0:
        if capture:
            if completed.stdout:
                print(completed.stdout, flush=True)
            if completed.stderr:
                print(completed.stderr, file=sys.stderr, flush=True)
        raise ReleaseError(f"Command failed exit={completed.returncode}: {display}")
    return completed


def git_changed_files(base_sha: str) -> list[str]:
    run(["git", "fetch", "--no-tags", "--depth=1", "origin", base_sha])
    result = run(
        ["git", "diff", "--name-only", f"{base_sha}..HEAD"],
        capture=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def package_equivalent_since(base_sha: str) -> tuple[bool, list[str]]:
    changed = git_changed_files(base_sha)
    return all(path.startswith(".github/") for path in changed), changed


def runtime_checkpoint_safe_since(base_sha: str) -> tuple[bool, list[str]]:
    allowed_exact = {
        "scripts/publish-step5-main-release.ps1",
        "scripts/release-only-recovery.ps1",
    }
    changed = git_changed_files(base_sha)
    safe = all(path.startswith(".github/") or path in allowed_exact for path in changed)
    return safe, changed


def validate_phase5_proof(proof: dict[str, Any]) -> None:
    require(int(proof.get("fps") or 0) == 30, "Phase-5 proof fps != 30")
    require(int(proof.get("rendered_frames") or 0) == 168, "Phase-5 proof frame count != 168")
    angles = proof.get("sampled_angles_degrees") or {}
    require(abs(float(angles.get("start") or 0.0)) <= 1.5, "Phase-5 start angle invalid")
    require(
        abs(float(angles.get("inverted") or 0.0) - 180.0) <= 2.0,
        "Phase-5 inverted angle invalid",
    )
    require(abs(float(angles.get("returned") or 0.0)) <= 2.0, "Phase-5 return angle invalid")
    require(bool(proof.get("warning_state_rendered")), "Phase-5 warning proof missing")
    require(bool(proof.get("preview_zoom_rendered")), "Phase-5 preview zoom proof missing")


def validate_v06_payload(root: pathlib.Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for rel in V06_SOURCE_ASSETS:
        path = root / rel
        require(path.is_file(), f"v0.6 payload missing {rel}")
        require(path.stat().st_size > 0, f"v0.6 payload empty {rel}")
        records.append(file_record(path, root))

    smoke = json_read(root / "dist/package-smoke.json")
    for key in ("app_is_packaged", "rendered", "polished", "bundled_python", "python_exec"):
        require(bool(smoke.get(key)), f"v0.6 package smoke failed field {key}")

    forgey = json_read(root / "dist/phase6-package-forgey-proof.json")
    require(forgey.get("selected_generation") == "G2", "v0.6 package proof not G2")
    require(int(forgey.get("forward_provider_calls") or 0) == 0, "v0.6 forward provider call")
    require(int(forgey.get("reverse_provider_calls") or 0) == 0, "v0.6 reverse provider call")
    require(
        int(forgey.get("native_vision_provider_calls") or 0) == 0,
        "v0.6 native vision provider call",
    )
    require(bool(forgey.get("vision_enabled")), "v0.6 vision disabled")
    require(int(forgey.get("vision_parameters") or 0) > 0, "v0.6 vision params missing")
    require(str(forgey.get("diagnostics") or "") == "44/44", "v0.6 diagnostics not 44/44")

    validate_phase5_proof(json_read(root / "proof/phase5/proof.json"))
    return records


def validate_v05_payload(root: pathlib.Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for rel in V05_SOURCE_ASSETS:
        path = root / rel
        require(path.is_file(), f"v0.5 payload missing {rel}")
        require(path.stat().st_size > 0, f"v0.5 payload empty {rel}")
        records.append(file_record(path, root))

    smoke = json_read(root / "dist/package-smoke.json")
    for key in ("app_is_packaged", "rendered", "polished", "bundled_python", "python_exec"):
        require(bool(smoke.get(key)), f"v0.5 package smoke failed field {key}")
    proof = json_read(root / "proof/phase5/proof.json")
    validate_phase5_proof(proof)
    stream = proof.get("sand_stream_opacity") or {}
    require(float(stream.get("flowing") or 0.0) >= 0.8, "v0.5 sand flow proof invalid")
    require(
        float(stream.get("pausedForFlip") or 1.0) <= 0.15,
        "v0.5 sand flip pause proof invalid",
    )
    require(
        float(stream.get("resumedAfterSettle") or 0.0) >= 0.8,
        "v0.5 sand resume proof invalid",
    )
    return records


def copy_payload(source_root: pathlib.Path, target_root: pathlib.Path, rel_paths: list[str]) -> None:
    for rel in rel_paths:
        source = source_root / rel
        require(source.is_file(), f"Payload copy source missing: {source}")
        target = target_root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def cache_v06_payload(source_sha: str, records: list[dict[str, Any]], provenance: dict[str, Any]) -> None:
    cache_dir = CACHE_ROOT / TARGET_SHA
    payload_dir = cache_dir / "payload"
    if payload_dir.exists():
        shutil.rmtree(payload_dir)
    payload_dir.mkdir(parents=True, exist_ok=True)
    copy_payload(WORKSPACE, payload_dir, V06_SOURCE_ASSETS)
    manifest = {
        "schema_version": 2,
        "status": "VERIFIED_FOR_RELEASE",
        "target_sha": TARGET_SHA,
        "payload_source_sha": source_sha,
        "created_utc": now_utc(),
        "provenance": provenance,
        "files": records,
    }
    json_write(cache_dir / "CACHE.json", manifest)
    (cache_dir / "VERIFIED.txt").write_text(
        f"target_sha={TARGET_SHA}\npayload_source_sha={source_sha}\nstatus=VERIFIED_FOR_RELEASE\n",
        encoding="ascii",
    )
    log(
        f"V06_CACHE_SAVED target={TARGET_SHA} payload_source={source_sha} "
        f"files={len(records)} path={payload_dir}"
    )


def discover_local_v06_cache() -> tuple[pathlib.Path, str, dict[str, Any]] | None:
    if not CACHE_ROOT.exists():
        return None
    candidates = [
        p
        for p in CACHE_ROOT.iterdir()
        if p.is_dir() and len(p.name) == 40 and all(c in "0123456789abcdefABCDEF" for c in p.name)
    ]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for candidate in candidates:
        payload = candidate / "payload"
        marker = candidate / "VERIFIED.txt"
        if not marker.is_file() or not payload.is_dir():
            continue
        try:
            equivalent, changed = package_equivalent_since(candidate.name)
            if not equivalent:
                log(
                    f"V06_CACHE_SKIP sha={candidate.name} reason=packaged-files-changed "
                    f"changed={','.join(changed)}"
                )
                continue
            validate_v06_payload(payload)
            meta = {}
            cache_json = candidate / "CACHE.json"
            if cache_json.is_file():
                meta = json_read(cache_json)
            log(
                f"V06_CACHE_SELECTED sha={candidate.name} changed_only={','.join(changed) or 'none'}"
            )
            return payload, candidate.name, meta
        except Exception as exc:
            log(f"V06_CACHE_SKIP sha={candidate.name} reason={type(exc).__name__}:{exc}")
    return None


def list_artifacts() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    page = 1
    while True:
        payload = api_request(
            "GET",
            f"/repos/{REPO}/actions/artifacts?per_page=100&page={page}",
        )
        require(isinstance(payload, dict), "Artifacts response is not an object")
        batch = payload.get("artifacts") or []
        require(isinstance(batch, list), "Artifacts response artifacts is not a list")
        results.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return results


def download_file(url: str, destination: pathlib.Path) -> None:
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": RELEASE_API_VERSION,
        "User-Agent": "EL-Bot-Release-Manager",
    }
    request = urllib.request.Request(url, headers=headers, method="GET")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(request, timeout=1800) as response, destination.open("wb") as out:
        shutil.copyfileobj(response, out, length=1024 * 1024)


def restore_artifact(artifact: dict[str, Any], inner_name: str, destination: pathlib.Path) -> None:
    artifact_id = int(artifact["id"])
    outer = RUNNER_TEMP / f"artifact-{artifact_id}.zip"
    stage = RUNNER_TEMP / f"artifact-{artifact_id}-{uuid.uuid4().hex}"
    if outer.exists():
        outer.unlink()
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir(parents=True)
    download_file(f"{API}/repos/{REPO}/actions/artifacts/{artifact_id}/zip", outer)
    with zipfile.ZipFile(outer) as archive:
        archive.extractall(stage)
    inner = stage / inner_name
    require(inner.is_file(), f"Artifact {artifact.get('name')} missing {inner_name}")
    with zipfile.ZipFile(inner) as archive:
        archive.extractall(destination)
    log(f"ARTIFACT_RESTORED id={artifact_id} name={artifact.get('name')}")


def ensure_python_torch() -> pathlib.Path:
    py_dir = TOOL_CACHE / "ELPython/3.12.10"
    python_exe = py_dir / "python.exe"
    require(python_exe.is_file(), "Cached Python 3.12.10 missing")
    torch_dir = TOOL_CACHE / "ELTorch/2.13.0-cp312"
    marker = torch_dir / ".ready"
    require(marker.is_file(), "Cached PyTorch 2.13 checkpoint missing")
    pth = py_dir / "python312._pth"
    require(pth.is_file(), "python312._pth missing")
    lines = [
        line
        for line in pth.read_text(encoding="utf-8").splitlines()
        if "ELTorch\\" not in line and "ELTorch/" not in line
    ]
    lines.append(str(torch_dir))
    if "import site" not in lines:
        lines.append("import site")
    pth.write_text("\n".join(lines) + "\n", encoding="utf-8")
    run(
        [
            str(python_exe),
            "-c",
            "import sys,torch;"
            "assert sys.version_info[:2]==(3,12);"
            "assert torch.__version__.startswith('2.13.0');"
            "print('PYTHON_TORCH_OK',sys.version.split()[0],torch.__version__)",
        ]
    )
    return python_exe


def package_smoke(
    executable: pathlib.Path,
    output: pathlib.Path,
    timeout_seconds: int,
    *,
    cwd: pathlib.Path | None = None,
) -> dict[str, Any]:
    if output.exists():
        output.unlink()
    env = os.environ.copy()
    env["EL_PACKAGE_SMOKE_FILE"] = str(output)
    env.pop("EL_PYTHON", None)
    process = subprocess.Popen([str(executable)], cwd=(cwd or WORKSPACE), env=env)
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=30)
        raise ReleaseError(f"Package smoke timed out: {executable}")
    require(return_code == 0, f"Package smoke exit {return_code}: {executable}")
    require(output.is_file(), f"Package smoke evidence missing: {output}")
    payload = json_read(output)
    for key in ("app_is_packaged", "rendered", "polished", "bundled_python", "python_exec"):
        require(bool(payload.get(key)), f"Package smoke failed field {key}: {executable}")
    return payload


def rebuild_v06_from_runtime_checkpoint() -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    artifacts = list_artifacts()
    candidates = [
        a
        for a in artifacts
        if not bool(a.get("expired"))
        and str(a.get("name") or "").startswith("phase6-runtime-visual-")
    ]
    candidates.sort(key=lambda a: str(a.get("created_at") or ""), reverse=True)
    selected: dict[str, Any] | None = None
    runtime_sha = ""
    changed: list[str] = []
    for artifact in candidates:
        name = str(artifact.get("name") or "")
        candidate_sha = name.removeprefix("phase6-runtime-visual-")
        if len(candidate_sha) != 40:
            continue
        safe, candidate_changed = runtime_checkpoint_safe_since(candidate_sha)
        if safe:
            selected = artifact
            runtime_sha = candidate_sha
            changed = candidate_changed
            break
    require(selected is not None, "No safe runtime/visual checkpoint available for v0.6 rebuild")
    log(
        f"V06_RUNTIME_CHECKPOINT_SELECTED sha={runtime_sha} "
        f"changed={','.join(changed) or 'none'}"
    )
    restore_artifact(selected, "phase6-runtime-visual.zip", WORKSPACE)

    node_version = run(["node", "--version"], capture=True).stdout.strip()
    require(node_version.startswith("v24."), f"Node 24 required for v0.6 rebuild, got {node_version}")
    python_exe = ensure_python_torch()
    env = os.environ.copy()
    env["EL_PYTHON"] = str(python_exe)
    env["PYTHONIOENCODING"] = "utf-8"

    run([str(python_exe), "architecture/verify_phase6_step5_release.py"], env=env)
    run(["npm", "install", "--no-audit", "--no-fund"], env=env)
    run([str(python_exe), "scripts/materialize-phase6-runtime.py"], env=env)
    registry = WORKSPACE / "data/phase6-step3/generation-registry.json"
    require(registry.is_file(), "v0.6 registry missing after materialization")
    env["EL_FORGEY_REGISTRY"] = str(registry)
    run(["node", "scripts/phase6-step4-runtime-proof.js"], env=env)
    run(
        [
            str(python_exe),
            "scripts/phase6-vision-infer.py",
            "--registry",
            str(registry),
            "--direction",
            "IMAGE_TO_EL",
            "--fixture-concept",
            "red-circle",
            "--fixture-seed",
            "9000",
            "--expected",
            "🔴",
            "--evidence",
            "data/phase6-step3/runtime-vision-proof.json",
        ],
        env=env,
    )
    run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/materialize-phase6-python.ps1",
        ],
        env=env,
        timeout=1200,
    )
    run(
        [
            str(WORKSPACE / "python/python.exe"),
            "-c",
            "import sys,torch;"
            "assert sys.version_info[:2]==(3,12);"
            "assert torch.__version__.startswith('2.13.0');"
            "print('EMBEDDED_OK',torch.__version__)",
        ],
        env=env,
    )
    run(["npm", "run", "build:windows"], env=env, timeout=2400)

    for rel in (
        "dist/win-unpacked/EL-Bot.exe",
        f"dist/EL-Bot-Setup-{VERSION}-x64.exe",
        f"dist/EL-Bot-Portable-{VERSION}-x64.exe",
    ):
        require((WORKSPACE / rel).is_file(), f"v0.6 package output missing {rel}")

    smoke_path = RUNNER_TEMP / "el-bot-v06-package-smoke.json"
    package_smoke(WORKSPACE / "dist/win-unpacked/EL-Bot.exe", smoke_path, 120, cwd=WORKSPACE)
    shutil.copy2(smoke_path, WORKSPACE / "dist/package-smoke.json")

    run([str(python_exe), "scripts/phase6-step5-package-forgey-proof.py"], env=env)
    run([str(python_exe), "architecture/verify_phase2_knowledge_foundation.py"], env=env)
    run([str(python_exe), "architecture/verify_phase3_semantic_search.py"], env=env)
    diag = (
        "import importlib.machinery,importlib.util,pathlib,sys;"
        "root=pathlib.Path('.');a=chr(0x1F9EA);"
        "p=next(x for x in root.rglob('*') if x.is_file() and x.name==a and x.parent.name==a);"
        "l=importlib.machinery.SourceFileLoader('_p6_release_diag',str(p));"
        "s=importlib.util.spec_from_loader('_p6_release_diag',l);"
        "m=importlib.util.module_from_spec(s);sys.modules['_p6_release_diag']=m;l.exec_module(m);"
        "r=m.DiagnosticsEngine().run();print(r.render_el());assert r.passed and len(r.checks)==44"
    )
    run([str(python_exe), "-c", diag], env=env)

    records = validate_v06_payload(WORKSPACE)
    provenance = {
        "mode": "runtime-visual-rebuild",
        "runtime_checkpoint_sha": runtime_sha,
        "checkpoint_diff": changed,
    }
    cache_v06_payload(TARGET_SHA, records, provenance)
    return TARGET_SHA, records, provenance


def preflight() -> None:
    branches = [str(b.get("name") or "") for b in list_branches()]
    require(branches == ["main"], f"Repository must be main-only; found branches={branches}")
    releases = list_releases()
    snapshot = []
    for release in releases:
        rid = int(release["id"])
        assets = list_assets(rid)
        snapshot.append(
            {
                "id": rid,
                "tag": str(release.get("tag_name") or ""),
                "target": str(release.get("target_commitish") or ""),
                "name": str(release.get("name") or ""),
                "assets": len(assets),
                "draft": bool(release.get("draft")),
                "prerelease": bool(release.get("prerelease")),
            }
        )
    state = {
        "schema_version": 2,
        "started_utc": now_utc(),
        "repository": REPO,
        "target_sha": TARGET_SHA,
        "target_tag": V06_TAG,
        "phase5_source_sha": PHASE5_SHA,
        "phase5_tag": V05_TAG,
        "initial_releases": snapshot,
    }
    state_save(state)
    log(
        "RELEASE_PREFLIGHT_OK "
        f"branches=main releases={len(snapshot)} target={TARGET_SHA} v06_tag={V06_TAG}"
    )
    for item in snapshot:
        log(
            f"RELEASE_PREFLIGHT_ITEM id={item['id']} tag={item['tag']} "
            f"target={item['target']} assets={item['assets']}"
        )


def prepare_v06() -> None:
    state = state_load()
    require(state.get("target_sha") == TARGET_SHA, "Release state target SHA mismatch")

    try:
        records = validate_v06_payload(WORKSPACE)
        provenance = {"mode": "workspace-certified", "payload_source_sha": TARGET_SHA}
        cache_v06_payload(TARGET_SHA, records, provenance)
        state["v06_payload"] = {
            "source_sha": TARGET_SHA,
            "mode": "workspace-certified",
            "records": records,
        }
        state_save(state)
        log(f"V06_PREPARE_OK mode=workspace-certified files={len(records)}")
        return
    except Exception as exc:
        log(f"V06_WORKSPACE_NOT_READY reason={type(exc).__name__}:{exc}")

    local = discover_local_v06_cache()
    if local:
        payload_root, source_sha, meta = local
        copy_payload(payload_root, WORKSPACE, V06_SOURCE_ASSETS)
        records = validate_v06_payload(WORKSPACE)
        equivalent, changed = package_equivalent_since(source_sha)
        require(equivalent, f"Selected local v0.6 cache invalidated: {changed}")
        provenance = {
            "mode": "local-certified-cache",
            "payload_source_sha": source_sha,
            "equivalent_to_target": True,
            "equivalence_rule": "only .github/** changed; package.json excludes .github/**",
            "changed_files": changed,
            "prior_cache": meta,
        }
        cache_v06_payload(source_sha, records, provenance)
        state["v06_payload"] = {
            "source_sha": source_sha,
            "mode": "local-certified-cache",
            "records": records,
            "changed_files": changed,
        }
        state_save(state)
        log(
            f"V06_PREPARE_OK mode=local-certified-cache source={source_sha} "
            f"target={TARGET_SHA} files={len(records)}"
        )
        return

    artifacts = list_artifacts()
    certified = [
        a
        for a in artifacts
        if not bool(a.get("expired"))
        and str(a.get("name") or "").startswith("phase6-certified-")
    ]
    certified.sort(key=lambda a: str(a.get("created_at") or ""), reverse=True)
    for artifact in certified:
        name = str(artifact.get("name") or "")
        source_sha = name.removeprefix("phase6-certified-")
        if len(source_sha) != 40:
            continue
        equivalent, changed = package_equivalent_since(source_sha)
        if not equivalent:
            continue
        restore_artifact(artifact, "phase6-certified.zip", WORKSPACE)
        records = validate_v06_payload(WORKSPACE)
        provenance = {
            "mode": "github-certified-artifact",
            "payload_source_sha": source_sha,
            "changed_files": changed,
        }
        cache_v06_payload(source_sha, records, provenance)
        state["v06_payload"] = {
            "source_sha": source_sha,
            "mode": "github-certified-artifact",
            "records": records,
            "changed_files": changed,
        }
        state_save(state)
        log(
            f"V06_PREPARE_OK mode=github-certified-artifact source={source_sha} "
            f"files={len(records)}"
        )
        return

    source_sha, records, provenance = rebuild_v06_from_runtime_checkpoint()
    state["v06_payload"] = {
        "source_sha": source_sha,
        "mode": provenance["mode"],
        "records": records,
        "provenance": provenance,
    }
    state_save(state)
    log(f"V06_PREPARE_OK mode=runtime-rebuild source={source_sha} files={len(records)}")


def release_is_v05_eligible(release: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    assets = list_assets(int(release["id"]))
    uploaded_names = {
        str(a.get("name") or "")
        for a in assets
        if str(a.get("state") or "") == "uploaded" and int(a.get("size") or 0) > 0
    }
    return REQUIRED_V05_CORE.issubset(uploaded_names), assets


def sha_matches(candidate: str, full_sha: str) -> bool:
    candidate = candidate.strip().lower()
    full_sha = full_sha.lower()
    return bool(candidate) and (full_sha.startswith(candidate) or candidate.startswith(full_sha))


def ensure_node22() -> tuple[pathlib.Path, dict[str, str], str]:
    index_url = "https://nodejs.org/dist/index.json"
    with urllib.request.urlopen(index_url, timeout=90) as response:
        versions = json.loads(response.read().decode("utf-8"))
    entry = next(
        (
            item
            for item in versions
            if str(item.get("version") or "").startswith("v22.")
            and "win-x64-zip" in (item.get("files") or [])
        ),
        None,
    )
    require(entry is not None, "Unable to resolve a Node 22 win-x64 distribution")
    version = str(entry["version"])
    install_dir = TOOL_CACHE / "ELNode" / version
    node_exe = install_dir / "node.exe"
    if not node_exe.is_file():
        zip_path = RUNNER_TEMP / f"node-{version}-win-x64.zip"
        extract_dir = RUNNER_TEMP / f"node-{version}-{uuid.uuid4().hex}"
        if zip_path.exists():
            zip_path.unlink()
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        url = f"https://nodejs.org/dist/{version}/node-{version}-win-x64.zip"
        log(f"NODE22_DOWNLOAD version={version}")
        with urllib.request.urlopen(url, timeout=900) as response, zip_path.open("wb") as out:
            shutil.copyfileobj(response, out, length=1024 * 1024)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(extract_dir)
        source_dirs = [p for p in extract_dir.iterdir() if p.is_dir()]
        require(len(source_dirs) == 1, "Unexpected Node 22 archive layout")
        if install_dir.exists():
            shutil.rmtree(install_dir)
        shutil.copytree(source_dirs[0], install_dir)
    env = os.environ.copy()
    env["PATH"] = str(install_dir) + os.pathsep + env.get("PATH", "")
    node_version = run([str(node_exe), "--version"], env=env, capture=True).stdout.strip()
    require(node_version.startswith("v22."), f"Historical Node major mismatch: {node_version}")
    log(f"NODE22_OK version={node_version}")
    return install_dir, env, node_version


def reconstruct_v05() -> tuple[dict[str, Any], pathlib.Path, list[dict[str, Any]], str]:
    rebuild_root = RUNNER_TEMP / f"phase5-rebuild-{uuid.uuid4().hex}"
    source_zip = RUNNER_TEMP / f"phase5-source-{uuid.uuid4().hex}.zip"
    rebuild_root.mkdir(parents=True, exist_ok=False)
    log(f"V05_RECONSTRUCT_BEGIN source_sha={PHASE5_SHA} root={rebuild_root}")
    try:
        run(["git", "fetch", "--no-tags", "--depth=1", "origin", PHASE5_SHA])
        run(
            [
                "git",
                "archive",
                "--format=zip",
                f"--output={source_zip}",
                PHASE5_SHA,
            ]
        )
        with zipfile.ZipFile(source_zip) as archive:
            archive.extractall(rebuild_root)

        _, node_env, node_version = ensure_node22()
        npm = shutil.which("npm.cmd", path=node_env["PATH"])
        require(npm is not None, "npm.cmd missing from Node 22 distribution")
        run([npm, "install", "--no-audit", "--no-fund"], cwd=rebuild_root, env=node_env, timeout=1200)
        run([npm, "run", "proof:visual"], cwd=rebuild_root, env=node_env, timeout=900)
        validate_phase5_proof(json_read(rebuild_root / "proof/phase5/proof.json"))
        proof = json_read(rebuild_root / "proof/phase5/proof.json")
        stream = proof.get("sand_stream_opacity") or {}
        require(float(stream.get("flowing") or 0.0) >= 0.8, "v0.5 proof flowing opacity invalid")
        require(float(stream.get("pausedForFlip") or 1.0) <= 0.15, "v0.5 proof flip pause invalid")
        require(float(stream.get("resumedAfterSettle") or 0.0) >= 0.8, "v0.5 proof resume invalid")

        run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                "scripts/materialize-python.ps1",
            ],
            cwd=rebuild_root,
            env=node_env,
            timeout=1200,
        )
        run([npm, "run", "build:windows", "--", "--publish", "never"], cwd=rebuild_root, env=node_env, timeout=2400)
        for rel in (
            "dist/win-unpacked/EL-Bot.exe",
            "dist/EL-Bot-Setup-0.5.0-x64.exe",
            "dist/EL-Bot-Portable-0.5.0-x64.exe",
        ):
            require((rebuild_root / rel).is_file(), f"Reconstructed v0.5 output missing {rel}")

        smoke_path = RUNNER_TEMP / f"phase5-smoke-{uuid.uuid4().hex}.json"
        package_smoke(rebuild_root / "dist/win-unpacked/EL-Bot.exe", smoke_path, 90, cwd=rebuild_root)
        shutil.copy2(smoke_path, rebuild_root / "dist/package-smoke.json")
        records = validate_v05_payload(rebuild_root)

        manifest = {
            "schema_version": 2,
            "phase": 5,
            "status": "RECONSTRUCTED_AND_RECERTIFIED",
            "version": PHASE5_VERSION,
            "source_commit_sha": PHASE5_SHA,
            "tag": V05_TAG,
            "reconstructed_utc": now_utc(),
            "reconstructed_by_release_workflow_commit": TARGET_SHA,
            "historical_ci_node_major": 22,
            "rebuild_node_version": node_version,
            "provenance_note": (
                "The original deleted binary assets were not recoverable byte-for-byte. "
                "These assets were rebuilt and re-certified from the exact historical "
                "Phase-5 source commit using the same Node 22 major specified by its CI."
            ),
            "assets": records,
        }
        json_write(rebuild_root / V05_MANIFEST, manifest)
        upload_files = [rebuild_root / rel for rel in V05_SOURCE_ASSETS + [V05_MANIFEST]]
        full_records = [file_record(path, rebuild_root) for path in upload_files]

        release = create_or_get_release(
            tag=V05_TAG,
            target_sha=PHASE5_SHA,
            name=f"EL Bot v0.5.0 - Phase 5 ({PHASE5_SHA[:12]})",
            body=(
                f"Reconstructed and re-certified Phase 5 Windows release from exact historical "
                f"source commit {PHASE5_SHA}. The original deleted binary bytes were not available, "
                f"so Setup and Portable were rebuilt from that source using Node 22 major to match "
                f"the historical CI. Includes packaged-runtime smoke evidence and freshly regenerated "
                f"30 FPS Phase-5 visual proof."
            ),
        )
        for path in upload_files:
            ensure_asset(release, path)

        release = get_release_by_tag(V05_TAG)
        require(release is not None, "Reconstructed v0.5 release disappeared after upload")
        verify_release_target(release, V05_TAG, PHASE5_SHA)
        assets = verified_asset_inventory(release, upload_files, exact=True)
        log(
            f"V05_RECONSTRUCT_OK tag={V05_TAG} assets={len(assets)} "
            f"source_sha={PHASE5_SHA} node={node_version}"
        )
        return release, rebuild_root, full_records, node_version
    except Exception:
        log(f"V05_RECONSTRUCT_FAILED forensic_root={rebuild_root}")
        raise


def ensure_v05() -> None:
    state = state_load()
    require(state.get("target_sha") == TARGET_SHA, "Release state target SHA mismatch")

    candidates = [
        r
        for r in list_releases()
        if str(r.get("tag_name") or "").startswith("el-bot-v0.5.0-")
    ]
    scored: list[tuple[tuple[int, int, str], dict[str, Any], list[dict[str, Any]]]] = []
    for release in candidates:
        eligible, assets = release_is_v05_eligible(release)
        if not eligible:
            continue
        target = str(release.get("target_commitish") or "")
        preferred = int(sha_matches(target, PHASE5_SHA))
        score = (preferred, len(assets), str(release.get("published_at") or ""))
        scored.append((score, release, assets))

    rebuild_root: pathlib.Path | None = None
    reconstructed_records: list[dict[str, Any]] | None = None
    preferred_scored = [item for item in scored if item[0][0] == 1]
    if preferred_scored:
        preferred_scored.sort(key=lambda item: item[0], reverse=True)
        _, keeper, assets = preferred_scored[0]
        tag = str(keeper.get("tag_name") or "")
        verify_release_target(keeper, tag, PHASE5_SHA)
        log(
            f"V05_KEEP_EXISTING id={keeper['id']} tag={tag} "
            f"assets={len(assets)} preferred=True"
        )
        mode = "existing-preferred"
        node_version = None
    else:
        if scored:
            log(
                "V05_WEAKER_RELEASES_PRESENT but no eligible c489 keeper survived; "
                "reconstructing the preferred historical c489 release"
            )
        keeper, rebuild_root, reconstructed_records, node_version = reconstruct_v05()
        assets = list_assets(int(keeper["id"]))
        mode = "reconstructed"

    eligible, refreshed_assets = release_is_v05_eligible(keeper)
    require(eligible, f"Selected v0.5 release is not installable: {keeper.get('tag_name')}")
    state["v05"] = {
        "id": int(keeper["id"]),
        "tag": str(keeper.get("tag_name") or ""),
        "target_sha": PHASE5_SHA,
        "mode": mode,
        "assets": len(refreshed_assets),
        "rebuild_node_version": node_version,
        "records": reconstructed_records,
    }
    state_save(state)
    if rebuild_root and rebuild_root.exists():
        shutil.rmtree(rebuild_root, ignore_errors=True)
    log(
        f"V05_ENSURE_OK mode={mode} tag={state['v05']['tag']} "
        f"assets={state['v05']['assets']}"
    )


def ensure_v06() -> None:
    state = state_load()
    payload = state.get("v06_payload")
    require(isinstance(payload, dict), "v0.6 payload was not prepared")
    validate_v06_payload(WORKSPACE)
    source_sha = str(payload.get("source_sha") or TARGET_SHA)

    manifest_assets = []
    for rel in V06_SOURCE_ASSETS:
        path = WORKSPACE / rel
        manifest_assets.append(file_record(path, WORKSPACE))
    manifest = {
        "schema_version": 4,
        "phase": 6,
        "step": 5,
        "status": "VERIFIED_FOR_RELEASE",
        "version": VERSION,
        "release_target_sha": TARGET_SHA,
        "payload_source_sha": source_sha,
        "tag": V06_TAG,
        "generated_utc": now_utc(),
        "modalities": ["text", "image"],
        "native_vision": True,
        "forgey_generation": "G2",
        "provider_free": True,
        "diagnostics": "44/44",
        "payload_mode": str(payload.get("mode") or ""),
        "payload_equivalence": (
            "Payload source differs from release target only by .github/** release tooling, "
            "which package.json excludes from the Windows package."
            if source_sha != TARGET_SHA
            else "Payload was certified for the release target commit."
        ),
        "assets": manifest_assets,
    }
    json_write(WORKSPACE / V06_MANIFEST, manifest)
    upload_files = [WORKSPACE / rel for rel in V06_SOURCE_ASSETS + [V06_MANIFEST]]

    release = create_or_get_release(
        tag=V06_TAG,
        target_sha=TARGET_SHA,
        name=f"EL Bot v0.6.0 - Phase 6 Multimodal Forgey Insta ({TARGET_SHA[:12]})",
        body=(
            f"Phase 6 certified Windows release for exact main commit {TARGET_SHA}. "
            f"Normal install flow: download EL-Bot-Setup-{VERSION}-x64.exe and run the NSIS "
            f"setup wizard. A portable x64 EXE is also included. Embedded Python 3.12.10 and "
            f"PyTorch 2.13 CPU, verified G1/G2 Forgey artifacts, provider-free text and native "
            f"image inference proof, 44/44 diagnostics, and retained Phase-5 visual proof are included."
        ),
    )
    for path in upload_files:
        ensure_asset(release, path)

    expected_names = {path.name for path in upload_files}
    current_assets = list_assets(int(release["id"]))
    for asset in current_assets:
        if str(asset.get("name") or "") not in expected_names:
            delete_asset(int(asset["id"]))

    release = get_release_by_tag(V06_TAG)
    require(release is not None, "v0.6 release disappeared after upload")
    verify_release_target(release, V06_TAG, TARGET_SHA)
    assets = verified_asset_inventory(release, upload_files, exact=True)
    require(len(assets) == 14, f"v0.6 must contain exactly 14 assets, found {len(assets)}")

    state["v06"] = {
        "id": int(release["id"]),
        "tag": V06_TAG,
        "target_sha": TARGET_SHA,
        "payload_source_sha": source_sha,
        "assets": 14,
        "url": str(release.get("html_url") or ""),
    }
    state_save(state)
    log(
        f"V06_ENSURE_OK tag={V06_TAG} target={TARGET_SHA} "
        f"payload_source={source_sha} assets=14"
    )


def matching_tag_refs(prefix: str) -> list[dict[str, Any]]:
    encoded = urllib.parse.quote(prefix, safe="")
    result = api_request("GET", f"/repos/{REPO}/git/matching-refs/tags/{encoded}")
    require(isinstance(result, list), f"Matching refs response is not a list for {prefix}")
    return result


def finalize() -> None:
    state = state_load()
    require(isinstance(state.get("v05"), dict), "v0.5 keeper not established")
    require(isinstance(state.get("v06"), dict), "v0.6 release not established")

    v05_tag = str(state["v05"]["tag"])
    v06_tag = str(state["v06"]["tag"])
    v05 = get_release_by_tag(v05_tag)
    v06 = get_release_by_tag(v06_tag)
    require(v05 is not None, "v0.5 keeper missing before cleanup")
    require(v06 is not None, "v0.6 keeper missing before cleanup")

    eligible5, _ = release_is_v05_eligible(v05)
    require(eligible5, "v0.5 keeper became non-installable before cleanup")
    if v05_tag == V05_TAG:
        verify_release_target(v05, v05_tag, PHASE5_SHA)

    verify_release_target(v06, V06_TAG, TARGET_SHA)
    v06_files = [WORKSPACE / rel for rel in V06_SOURCE_ASSETS + [V06_MANIFEST]]
    assets6 = verified_asset_inventory(v06, v06_files, exact=True)
    require(len(assets6) == 14, "v0.6 lost its 14-asset contract before cleanup")

    keep_ids = {int(v05["id"]), int(v06["id"])}
    history = list_releases()
    log(
        f"RELEASE_CLEANUP_BEGIN total={len(history)} keep_v05={v05_tag} keep_v06={v06_tag}"
    )
    for release in history:
        if int(release["id"]) in keep_ids:
            continue
        delete_release(release, delete_associated_tag=True)

    keep_tags = {v05_tag, v06_tag}
    for prefix in ("el-bot-v0.5.0-", "el-bot-v0.6.0-"):
        for ref in matching_tag_refs(prefix):
            ref_name = str(ref.get("ref") or "")
            tag = ref_name.removeprefix("refs/tags/")
            if tag and tag not in keep_tags:
                delete_tag(tag)

    final_history = list_releases()
    require(
        len(final_history) == 2,
        f"Final release invariant failed: expected exactly 2 releases, found {len(final_history)}",
    )
    final_by_tag = {str(r.get("tag_name") or ""): r for r in final_history}
    require(set(final_by_tag) == keep_tags, f"Final release tags mismatch: {set(final_by_tag)}")

    final_v05 = final_by_tag[v05_tag]
    final_v06 = final_by_tag[v06_tag]
    eligible5, final_assets5 = release_is_v05_eligible(final_v05)
    require(eligible5, "Final v0.5 release is not installable")
    if v05_tag == V05_TAG:
        verify_release_target(final_v05, v05_tag, PHASE5_SHA)
    recorded_v05 = state["v05"].get("records")
    if isinstance(recorded_v05, list) and recorded_v05:
        final_assets5 = verify_remote_records(final_v05, recorded_v05, exact=True)

    verify_release_target(final_v06, V06_TAG, TARGET_SHA)
    final_assets6 = verified_asset_inventory(final_v06, v06_files, exact=True)
    require(len(final_assets6) == 14, "Final v0.6 asset count is not 14")

    branches = [str(b.get("name") or "") for b in list_branches()]
    require(branches == ["main"], f"Final branch invariant failed: {branches}")

    evidence = {
        "schema_version": 2,
        "status": "RELEASE_HISTORY_VERIFIED",
        "verified_utc": now_utc(),
        "repository": REPO,
        "branches": branches,
        "release_count": 2,
        "v0.5.0": {
            "tag": v05_tag,
            "release_id": int(final_v05["id"]),
            "assets": len(final_assets5),
            "installable": True,
            "mode": state["v05"].get("mode"),
            "historical_source_sha": PHASE5_SHA,
        },
        "v0.6.0": {
            "tag": V06_TAG,
            "release_id": int(final_v06["id"]),
            "target_sha": TARGET_SHA,
            "payload_source_sha": state["v06"].get("payload_source_sha"),
            "assets": 14,
            "url": str(final_v06.get("html_url") or ""),
        },
    }
    json_write(WORKSPACE / "dist/phase6-release-evidence.json", evidence)
    state["final"] = evidence
    state_save(state)
    log(
        f"PHASE6_RELEASE_OK releases=2 v05={v05_tag} v05_assets={len(final_assets5)} "
        f"v06={V06_TAG} v06_assets=14 main_only=PASS url={evidence['v0.6.0']['url']}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="EL Bot transactional release manager")
    parser.add_argument(
        "command",
        choices=["preflight", "prepare-v06", "ensure-v05", "ensure-v06", "finalize"],
    )
    args = parser.parse_args()
    commands = {
        "preflight": preflight,
        "prepare-v06": prepare_v06,
        "ensure-v05": ensure_v05,
        "ensure-v06": ensure_v06,
        "finalize": finalize,
    }
    try:
        commands[args.command]()
        return 0
    except Exception as exc:
        log(f"RELEASE_MANAGER_FAIL command={args.command} type={type(exc).__name__} error={exc}")
        raise


if __name__ == "__main__":
    raise SystemExit(main())
