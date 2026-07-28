"""ComfyUI job submission with full metadata capture.

Separate from `comfyui.py`, which stays read-only. This module queues work.

Every submission records the exact graph, the resolved seed, the model, and the
output hashes, so any panel can be reproduced or diagnosed later. The previous
system lost all of that: it queued graphs and kept nothing but the PNGs.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_HOST = "http://127.0.0.1:8188"


@dataclass
class JobResult:
    prompt_id: str
    ok: bool
    images: list[Path] = field(default_factory=list)
    error: str = ""
    seconds: float = 0.0
    graph: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "prompt_id": self.prompt_id,
            "ok": self.ok,
            "error": self.error,
            "seconds": round(self.seconds, 1),
            "images": [p.as_posix() for p in self.images],
        }


class ComfyClient:
    """Submit graphs, wait for completion, collect outputs."""

    def __init__(self, host: str = DEFAULT_HOST, timeout: int = 900):
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.client_id = str(uuid.uuid4())

    # -- plumbing ----------------------------------------------------------
    def _post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}{path}", data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(f"{self.host}{path}", timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))

    def reachable(self) -> bool:
        try:
            self._get("/system_stats")
            return True
        except Exception:
            return False

    def upload_image(self, path: Path, subfolder: str = "bananalab") -> str:
        """Push a local image into ComfyUI's input directory via the API.

        Returns the name LoadImage should use. Going through the API rather than
        copying into the input directory keeps the pipeline working even if the
        ComfyUI host is not this machine.
        """
        boundary = "----bananalab" + uuid.uuid4().hex
        name = path.name
        parts: list[bytes] = []

        def field(key: str, value: str) -> None:
            parts.append(
                f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n'
                f"{value}\r\n".encode()
            )

        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="image"; '
            f'filename="{name}"\r\nContent-Type: image/png\r\n\r\n'.encode()
        )
        parts.append(path.read_bytes())
        parts.append(b"\r\n")
        field("overwrite", "true")
        if subfolder:
            field("subfolder", subfolder)
        parts.append(f"--{boundary}--\r\n".encode())

        body = b"".join(parts)
        req = urllib.request.Request(
            f"{self.host}/upload/image", data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            info = json.loads(response.read().decode("utf-8"))
        sub = info.get("subfolder") or ""
        return f"{sub}/{info['name']}" if sub else info["name"]

    # -- execution ---------------------------------------------------------
    def submit(self, graph: dict) -> str:
        result = self._post("/prompt", {"prompt": graph, "client_id": self.client_id})
        if "prompt_id" not in result:
            raise RuntimeError(f"submit rejected: {result}")
        return result["prompt_id"]

    def wait(self, prompt_id: str, poll: float = 2.0) -> dict:
        """Poll history until the job appears. Raises on timeout."""
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            try:
                history = self._get(f"/history/{prompt_id}")
            except urllib.error.URLError:
                time.sleep(poll)
                continue
            if prompt_id in history:
                return history[prompt_id]
            time.sleep(poll)
        raise TimeoutError(f"{prompt_id} did not finish within {self.timeout}s")

    def fetch_outputs(self, entry: dict, dest_dir: Path, stem: str) -> list[Path]:
        """Download every produced image into dest_dir with deterministic names."""
        dest_dir.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        index = 0
        for node_output in (entry.get("outputs") or {}).values():
            for image in node_output.get("images") or []:
                if image.get("type") != "output":
                    continue
                query = urllib.parse.urlencode(
                    {
                        "filename": image["filename"],
                        "subfolder": image.get("subfolder", ""),
                        "type": image["type"],
                    }
                )
                with urllib.request.urlopen(f"{self.host}/view?{query}", timeout=180) as r:
                    data = r.read()
                suffix = f"_{index:02d}" if index else ""
                target = dest_dir / f"{stem}{suffix}.png"
                target.write_bytes(data)
                saved.append(target)
                index += 1
        return saved

    def run(self, graph: dict, dest_dir: Path, stem: str) -> JobResult:
        """Submit, wait, collect. One call per generation."""
        started = time.time()
        try:
            prompt_id = self.submit(graph)
        except Exception as exc:
            return JobResult("", False, error=f"submit failed: {exc}", graph=graph)

        try:
            entry = self.wait(prompt_id)
        except TimeoutError as exc:
            return JobResult(prompt_id, False, error=str(exc), graph=graph)

        status = (entry.get("status") or {}).get("status_str", "")
        if status == "error":
            messages = (entry.get("status") or {}).get("messages", [])
            detail = json.dumps(messages)[:800]
            return JobResult(prompt_id, False, error=f"execution error: {detail}", graph=graph)

        images = self.fetch_outputs(entry, dest_dir, stem)
        elapsed = time.time() - started
        if not images:
            return JobResult(prompt_id, False, error="no images produced",
                             seconds=elapsed, graph=graph)
        return JobResult(prompt_id, True, images=images, seconds=elapsed, graph=graph)


def sha256_of(path: Path) -> str:
    """Hash of the file as stored on disk, including embedded metadata."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pixel_sha256_of(path: Path) -> str:
    """Hash of the decoded pixels only, ignoring container metadata.

    Experiment 006: two runs of an identical graph produced different FILE
    hashes but identical PIXELS. ComfyUI embeds the prompt graph in a PNG text
    chunk, and that graph contains the SaveImage filename_prefix - so changing
    only the output name changes the file hash while the image is untouched.

    Regression checks and duplicate detection must use this, not the file hash,
    or they will report drift that did not happen.
    """
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - Pillow is a declared dependency
        return ""
    with Image.open(path) as image:
        return hashlib.sha256(image.convert("RGB").tobytes()).hexdigest()


def write_job_manifest(
    manifest_path: Path,
    *,
    job_id: str,
    job_class: str,
    workflow_version: str,
    graph: dict,
    result: JobResult,
    extra: dict | None = None,
) -> Path:
    """Record everything needed to reproduce or diagnose this generation."""
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "job_id": job_id,
        "job_class": job_class,
        "workflow_version": workflow_version,
        "prompt_id": result.prompt_id,
        "ok": result.ok,
        "error": result.error,
        "seconds": round(result.seconds, 1),
        "outputs": [
            {
                "path": p.as_posix(),
                "sha256": sha256_of(p),
                # The reproducibility hash. See pixel_sha256_of.
                "pixel_sha256": pixel_sha256_of(p),
                "bytes": p.stat().st_size,
            }
            for p in result.images
        ],
        "graph": graph,
        "review_status": "candidate",
        "reviewed_by": "",
        "review_note": "",
    }
    if extra:
        payload.update(extra)
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return manifest_path


def archive_graph(graph: dict, path: Path) -> Path:
    """Save the exact API graph beside its outputs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(graph, indent=2), encoding="utf-8")
    return path


def copy_into(src: Path, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return dest
