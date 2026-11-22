"""Static Dockerfile linting for /lint and /optimize.

Rules favour precision over recall: a finding must be something the writer
can act on. Things the parser cannot decide with confidence (dynamic ARG
base images, shell code inside strings, non-command positions) are left
alone rather than guessed at.

Rule IDs follow hadolint where the semantics match exactly (DL30xx); the
C10xx rules are this repo's own:

  DL3003  use WORKDIR instead of cd
  DL3004  do not use sudo
  DL3005  do not use apt-get upgrade / dist-upgrade
  DL3006  tag the base image version
  DL3007  do not use the :latest tag
  DL3009  rm -rf /var/lib/apt/lists/* in the same RUN as apt-get install
  DL3015  apt-get install --no-install-recommends
  DL3020  use COPY instead of ADD for local files
  C1001   COPY . . before the dependency install busts the cache
  C1002   credential-shaped ENV/ARG names bake secrets into image history
"""

import json
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Instruction:
    name: str
    value: str
    line: int


@dataclass(frozen=True)
class Finding:
    rule: str
    line: int
    message: str


_INSTRUCTION_RE = re.compile(r"^\s*([A-Za-z]+)\s+(.*)$", re.DOTALL)
_ARCHIVE_SUFFIXES = (
    ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz", ".tar.xz", ".txz",
    ".gz", ".bz2", ".xz",
)
_SECRET_KEY_RE = re.compile(
    r"(?i)(^|[_-])(password|passwd|secret|token|api[_-]?key|apikey"
    r"|access[_-]?key|private[_-]?key|credentials?)([_-]|$)"
)
_ENV_KEY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_-]*)\s*=")


def _logical_lines(text: str) -> List[Tuple[int, str]]:
    """Join backslash continuations; return (start_line, logical_line)."""
    out: List[Tuple[int, str]] = []
    buf: List[str] = []
    start = 0
    for lineno, raw in enumerate(text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), 1):
        stripped = raw.strip()
        if not buf:
            if not stripped or stripped.startswith("#"):
                continue
            start = lineno
            buf = [raw]
        else:
            if not stripped or stripped.startswith("#"):
                continue
            buf.append(raw)
        if buf[-1].rstrip().endswith("\\"):
            continue
        out.append((start, _join(buf)))
        buf = []
    if buf:
        out.append((start, _join(buf)))
    return out


def _join(buf: List[str]) -> str:
    return re.sub(r"\\[ \t]*\n\s*", " ", "\n".join(buf))


def parse_instructions(text: str) -> List[Instruction]:
    instructions = []
    for line, logical in _logical_lines(text):
        m = _INSTRUCTION_RE.match(logical)
        if not m:
            continue
        instructions.append(Instruction(m.group(1).upper(), m.group(2).strip(), line))
    return instructions


def _segments(run_value: str) -> List[str]:
    segs = []
    for part in re.split(r"&&|\|\||;", run_value):
        s = part.strip().lstrip("(").strip()
        if s:
            segs.append(s)
    return segs


def _seg_cmd(seg: str) -> Tuple[str, List[str]]:
    tokens = seg.split()
    return (tokens[0], tokens[1:]) if tokens else ("", [])


def _copy_parts(value: str) -> Tuple[List[str], str]:
    v = value.strip()
    if v.startswith("["):
        try:
            tokens = [str(x) for x in json.loads(v)]
        except ValueError:
            tokens = v.split()
    else:
        tokens = v.split()
    while tokens and tokens[0].startswith("--"):
        tokens.pop(0)
    return tokens[:-1], (tokens[-1] if tokens else "")


def _is_manifest_install(seg: str) -> bool:
    cmd, args = _seg_cmd(seg)
    if cmd in ("pip", "pip3"):
        return bool(re.search(r"(-r\b|requirements|pyproject|setup\.py)", seg))
    if cmd == "npm":
        return bool(args) and args[0] in ("ci", "install", "i")
    if cmd == "yarn":
        return bool(args) and args[0] in ("add", "install")
    if cmd == "pnpm":
        return bool(args) and args[0] == "install"
    return False


def _check_from(instr: Instruction, stage_names: set, out: List[Finding]) -> None:
    tokens = instr.value.split()
    while tokens and tokens[0].startswith("--"):
        tokens.pop(0)
    if not tokens:
        return
    ref = tokens[0]
    if len(tokens) >= 3 and tokens[1].upper() == "AS":
        stage_names.add(tokens[2].lower())
    if ref.lower() == "scratch" or "$" in ref:
        return
    ref_no_digest, _, has_digest = ref.partition("@")
    last = ref_no_digest.rsplit("/", 1)[-1]
    tag = last.split(":", 1)[1] if ":" in last else None
    base_name = last.split(":", 1)[0].lower()
    if "/" not in ref_no_digest and base_name in stage_names:
        return  # multi-stage reference, not a registry image
    if has_digest:
        return  # a digest pins content whatever the tag says
    if tag is None:
        out.append(Finding(
            "DL3006", instr.line,
            f"image '{ref}' has no tag; pin a version (e.g. {ref}:3.12-slim)",
        ))
    elif tag == "latest":
        out.append(Finding(
            "DL3007", instr.line,
            f"image '{base_name}' uses the :latest tag; pin an explicit version",
        ))


def _check_run(instr: Instruction, out: List[Finding]) -> None:
    value = instr.value
    for seg in _segments(value):
        cmd, args = _seg_cmd(seg)
        if cmd == "cd":
            out.append(Finding(
                "DL3003", instr.line,
                "use WORKDIR instead of cd; layer state does not carry cd across RUNs",
            ))
        elif cmd == "sudo":
            out.append(Finding(
                "DL3004", instr.line,
                "do not use sudo; the build already runs as root",
            ))
        elif cmd in ("apt", "apt-get") and args:
            if args[0] in ("upgrade", "dist-upgrade"):
                out.append(Finding(
                    "DL3005", instr.line,
                    "do not use apt-get upgrade; rebuild from a newer base image instead",
                ))
            elif args[0] == "install":
                if "--no-install-recommends" not in seg:
                    out.append(Finding(
                        "DL3015", instr.line,
                        "add --no-install-recommends to apt-get install to keep the layer small",
                    ))
                if "/var/lib/apt/lists" not in value:
                    out.append(Finding(
                        "DL3009", instr.line,
                        "run rm -rf /var/lib/apt/lists/* in the same RUN as apt-get install",
                    ))


def _check_add(instr: Instruction, out: List[Finding]) -> None:
    sources, _ = _copy_parts(instr.value)
    for src in sources:
        if src.startswith(("http://", "https://")):
            continue
        if src.lower().endswith(_ARCHIVE_SUFFIXES):
            continue
        out.append(Finding(
            "DL3020", instr.line,
            "use COPY for local files; ADD is for URLs and archives",
        ))
        return


def _check_env_arg(instr: Instruction, out: List[Finding]) -> None:
    value = instr.value
    keys = [m.group(1) for m in _ENV_KEY_RE.finditer(value)]
    if "=" not in value and value.split():
        keys.append(value.split()[0])
    for key in keys:
        if _SECRET_KEY_RE.search(key):
            out.append(Finding(
                "C1002", instr.line,
                f"{key} looks like a credential; {instr.name} values are baked into "
                "image history — pass at runtime or use a BuildKit secret mount",
            ))


def _check_copy_cache(instr: Instruction, out: List[Finding]) -> None:
    sources, _ = _copy_parts(instr.value)
    if not any(src in (".", "./", "./.") for src in sources):
        return
    out.append(Finding(
        "C1001", instr.line,
        "COPY . . before the dependency install invalidates the dependency layer "
        "on every code change; copy manifests first, install, then copy sources",
    ))


def lint(dockerfile: str) -> List[Finding]:
    instructions = parse_instructions(dockerfile)
    install_lines = [
        i.line for i in instructions
        if i.name == "RUN" and any(_is_manifest_install(s) for s in _segments(i.value))
    ]
    first_install = min(install_lines) if install_lines else None

    stage_names: set = set()
    out: List[Finding] = []
    for instr in instructions:
        if instr.name == "FROM":
            _check_from(instr, stage_names, out)
        elif instr.name == "RUN":
            _check_run(instr, out)
        elif instr.name == "ADD":
            _check_add(instr, out)
        elif instr.name in ("ENV", "ARG"):
            _check_env_arg(instr, out)
        if instr.name in ("COPY", "ADD") and first_install is not None and instr.line < first_install:
            _check_copy_cache(instr, out)
    return sorted(out, key=lambda f: (f.line, f.rule))


def format_findings(findings: List[Finding]) -> List[str]:
    return [f"L{f.line} [{f.rule}] {f.message}" for f in findings]
