#!/usr/bin/env python3
"""Create a deterministic, append-only, 10,000-commit growth history."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GROWTH = ROOT / "growth"
LEDGER = GROWTH / "shoots.jsonl"
STATE = GROWTH / "state.json"
SNAPSHOT = GROWTH / "organism.json"
SVG = GROWTH / "organism.svg"
DEFAULT_SEED = "epicormic-growth-v1"
OUTPUTS = (LEDGER, STATE, SNAPSHOT, SVG)


class GrowthError(RuntimeError):
    pass


def canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def digest_payload(payload: dict) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def make_record(index: int, previous_hash: str, seed: str, records: list[dict]) -> dict:
    if index == 0:
        payload = {
            "angle_delta": 0.0,
            "color": "#593a22",
            "id": 0,
            "length": 0.0,
            "parent": None,
            "previous_record_hash": "0" * 64,
            "seed": seed,
            "thickness": 8.0,
        }
    else:
        entropy = hashlib.sha256(f"{seed}:{index}".encode()).digest()
        parent = int.from_bytes(entropy[:8], "big") % index
        parent_thickness = float(records[parent]["thickness"])
        hue = 88 + entropy[8] % 42
        saturation = 34 + entropy[9] % 38
        lightness = 27 + entropy[10] % 34
        payload = {
            "angle_delta": round(-58.0 + int.from_bytes(entropy[11:13], "big") / 65535 * 116.0, 6),
            "color": f"hsl({hue} {saturation}% {lightness}%)",
            "id": index,
            "length": round(5.0 + int.from_bytes(entropy[13:15], "big") / 65535 * 14.0, 6),
            "parent": parent,
            "previous_record_hash": previous_hash,
            "seed": seed,
            "thickness": round(max(0.35, parent_thickness * (0.91 + entropy[15] / 2550)), 6),
        }
    return {**payload, "record_hash": digest_payload(payload)}


def read_ledger(path: Path = LEDGER) -> list[dict]:
    records = []
    if not path.exists():
        raise GrowthError(f"missing ledger: {path}")
    previous = "0" * 64
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw:
            raise GrowthError(f"blank ledger line {line_number}")
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as error:
            raise GrowthError(f"invalid JSON on ledger line {line_number}: {error}") from error
        if raw != canonical(record):
            raise GrowthError(f"ledger line {line_number} is not canonical JSON")
        if record.get("id") != line_number - 1:
            raise GrowthError(f"non-consecutive id on ledger line {line_number}")
        if record.get("previous_record_hash") != previous:
            raise GrowthError(f"broken hash chain on ledger line {line_number}")
        claimed = record.get("record_hash")
        payload = {key: value for key, value in record.items() if key != "record_hash"}
        if claimed != digest_payload(payload):
            raise GrowthError(f"invalid record hash on ledger line {line_number}")
        parent = record.get("parent")
        if record["id"] == 0:
            if parent is not None:
                raise GrowthError("record 0 must be the dormant trunk")
        elif not isinstance(parent, int) or parent < 0 or parent >= record["id"]:
            raise GrowthError(f"invalid parent on ledger line {line_number}")
        records.append(record)
        previous = claimed
    if not records:
        raise GrowthError("ledger has no dormant trunk record")
    return records


def geometry(records: list[dict]) -> list[dict]:
    points = []
    for record in records:
        if record["id"] == 0:
            points.append({**record, "angle": -90.0, "x0": 500.0, "y0": 960.0, "x1": 500.0, "y1": 940.0})
            continue
        parent = points[record["parent"]]
        angle = parent["angle"] + record["angle_delta"]
        radians = math.radians(angle)
        x0, y0 = parent["x1"], parent["y1"]
        x1 = x0 + math.cos(radians) * record["length"]
        y1 = y0 + math.sin(radians) * record["length"]
        points.append({**record, "angle": round(angle, 6), "x0": round(x0, 6), "y0": round(y0, 6), "x1": round(x1, 6), "y1": round(y1, 6)})
    return points


def render(records: list[dict]) -> dict[Path, str]:
    points = geometry(records)
    snapshot = canonical({"format": "epicormic-growth/v1", "record_count": len(records), "shoot_count": len(records) - 1, "shoots": points}) + "\n"
    state = canonical({"format": "epicormic-growth-state/v1", "last_record_hash": records[-1]["record_hash"], "next_id": len(records), "seed": records[0]["seed"], "shoot_count": len(records) - 1}) + "\n"
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000" role="img" aria-labelledby="title desc">',
        f'<title id="title">Epicormic growth after {len(records) - 1} shoots</title>',
        '<desc id="desc">A deterministic branching organism reconstructed from the append-only growth ledger.</desc>',
        '<rect width="1000" height="1000" fill="#f3efe3"/>',
        '<g fill="none" stroke-linecap="round">',
        '<path d="M500 970 L500 940" stroke="#593a22" stroke-width="12"/>',
    ]
    for point in points[1:]:
        lines.append(
            f'<path d="M{point["x0"]:.3f} {point["y0"]:.3f} L{point["x1"]:.3f} {point["y1"]:.3f}" '
            f'stroke="{point["color"]}" stroke-width="{point["thickness"]:.3f}" data-shoot="{point["id"]}"/>'
        )
    lines.extend(["</g>", f'<text x="24" y="40" font-family="monospace" font-size="18" fill="#382a1e">shoots: {len(records) - 1:05d}</text>', "</svg>", ""])
    return {STATE: state, SNAPSHOT: snapshot, SVG: "\n".join(lines)}


def git(*args: str, capture: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=capture)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise GrowthError(f"git {' '.join(args)} failed: {detail}")
    return (result.stdout or "").strip()


def require_repository(push_every: int) -> str:
    if git("rev-parse", "--show-toplevel") != str(ROOT):
        raise GrowthError("run from the Epicormic-Growth repository")
    if git("status", "--porcelain"):
        raise GrowthError("worktree must be clean before growth begins")
    branch = git("symbolic-ref", "--quiet", "--short", "HEAD")
    if not branch:
        raise GrowthError("detached HEAD is not permitted")
    if push_every:
        git("rev-parse", "--abbrev-ref", "@{upstream}")
        git("fetch", "--quiet")
        counts = git("rev-list", "--left-right", "--count", "HEAD...@{upstream}").split()
        if counts != ["0", "0"]:
            raise GrowthError("HEAD and its upstream must agree before a push-each run")
    return branch


def verify_staged_append(old_ledger: bytes) -> None:
    if not LEDGER.read_bytes().startswith(old_ledger):
        raise GrowthError("ledger prefix changed instead of growing")
    delta = LEDGER.read_bytes()[len(old_ledger):]
    if delta.count(b"\n") != 1 or not delta.endswith(b"\n"):
        raise GrowthError("a growth commit must append exactly one ledger line")
    staged = set(git("diff", "--cached", "--name-only").splitlines())
    expected = {str(path.relative_to(ROOT)) for path in OUTPUTS}
    if staged != expected:
        raise GrowthError(f"unexpected staged paths: {sorted(staged ^ expected)}")


def preview(records: list[dict], target: int, seed: str) -> None:
    current = len(records) - 1
    print(f"verified shoots : {current}")
    print(f"target commits  : {target}")
    print(f"remaining       : {target - current}")
    print(f"branch          : {git('symbolic-ref', '--quiet', '--short', 'HEAD')}")
    prior = records[-1]["record_hash"]
    sample_records = list(records)
    for index in range(len(records), min(target + 1, len(records) + 5)):
        record = make_record(index, prior, seed, sample_records)
        print(f"next {index:05d}       : parent {record['parent']:05d}, angle {record['angle_delta']:+.3f}, length {record['length']:.3f}")
        sample_records.append(record)
        prior = record["record_hash"]
    print("mode            : DRY RUN (pass --execute to create commits)")


def run(args: argparse.Namespace) -> int:
    require_repository(args.push_every)
    records = read_ledger()
    seed = records[0]["seed"]
    current = len(records) - 1
    if args.target < current:
        raise GrowthError(f"target {args.target} is behind current growth {current}")
    if not args.execute:
        preview(records, args.target, seed)
        return 0
    if args.target == current:
        print(f"already complete at {current} shoots")
        return 0

    for index in range(current + 1, args.target + 1):
        old_ledger = LEDGER.read_bytes()
        record = make_record(index, records[-1]["record_hash"], seed, records)
        with LEDGER.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(canonical(record) + "\n")
        records.append(record)
        for path, content in render(records).items():
            path.write_text(content, encoding="utf-8", newline="\n")
        git("add", *(str(path.relative_to(ROOT)) for path in OUTPUTS))
        verify_staged_append(old_ledger)
        git("commit", "-m", f"Grow shoot {index:05d} from {record['parent']:05d}")
        print(f"[{index:05d}/{args.target:05d}] parent={record['parent']:05d} hash={record['record_hash'][:12]}")
        if args.push_every and index % args.push_every == 0:
            git("push", capture=False)
        if args.delay:
            time.sleep(args.delay)
    if args.push_every and args.target % args.push_every:
        git("push", capture=False)
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=int, default=10_000, help="final generated shoot count (default: 10000)")
    parser.add_argument("--execute", action="store_true", help="create commits; without this flag, only validate and preview")
    parser.add_argument("--push-every", type=int, default=0, metavar="N", help="push after every N commits; 0 keeps all commits local")
    parser.add_argument("--delay", type=float, default=0.0, metavar="SECONDS", help="optional pause after each commit")
    args = parser.parse_args(argv)
    if args.target < 0 or args.push_every < 0 or args.delay < 0:
        parser.error("target, push interval and delay must be non-negative")
    return args


def main(argv: list[str] | None = None) -> int:
    try:
        return run(parse_args(sys.argv[1:] if argv is None else argv))
    except (GrowthError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
