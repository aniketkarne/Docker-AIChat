"""Tests for the static Dockerfile linter (backend/docker_lint.py).

Self-contained: puts the backend dir on sys.path itself so the suite runs
with plain `python -m pytest` from either the repo root or backend/.
"""

import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from docker_lint import format_findings, lint  # noqa: E402


# Every rule fires at least once. Line numbers below are 1-based and count
# the leading `# syntax` directive comment.
BAD_DOCKERFILE = """\
# syntax=docker/dockerfile:1
FROM ubuntu:latest AS build
RUN apt-get update && \\
    apt-get install -y curl
RUN cd /tmp && sudo make install
RUN apt-get upgrade
ADD app /opt/app
ADD app.tar.gz /opt/
ENV NPM_TOKEN=abc
COPY . .
RUN pip install -r requirements.txt
FROM build
CMD ["python", "app.py"]
"""

BAD_EXPECTED = [
    (2, "DL3007"),
    (3, "DL3009"),
    (3, "DL3015"),
    (5, "DL3003"),
    (5, "DL3004"),
    (6, "DL3005"),
    (7, "DL3020"),
    (9, "C1002"),
    (10, "C1001"),
]


def pairs(findings):
    return [(f.line, f.rule) for f in findings]


def test_bad_fixture_fires_every_rule():
    assert pairs(lint(BAD_DOCKERFILE)) == BAD_EXPECTED


def test_findings_sorted_by_line():
    found = pairs(lint(BAD_DOCKERFILE))
    assert found == sorted(found)


def test_empty_input():
    assert lint("") == []


def test_repo_backend_dockerfile_is_clean():
    """The backend image is written the way the rules demand: keep it clean."""
    text = (BACKEND_DIR / "Dockerfile").read_text()
    assert lint(text) == []


def test_repo_frontend_dockerfile_is_clean():
    text = (REPO_ROOT / "frontend" / "Dockerfile").read_text()
    assert lint(text) == []


def test_stage_refs_scratch_and_dynamic_base_are_not_flagged():
    text = (
        "FROM alpine:3.20 AS base\n"
        "FROM base\n"
        "FROM scratch\n"
        "ARG BASE_IMAGE=python:3.11-slim\n"
        "FROM ${BASE_IMAGE}\n"
    )
    assert lint(text) == []


def test_untagged_registry_image_is_flagged():
    found = lint("FROM localhost:5000/myapp\n")
    assert pairs(found) == [(1, "DL3006")]


def test_untagged_official_image_is_flagged():
    found = lint("FROM python\n")
    assert pairs(found) == [(1, "DL3006")]


def test_digest_pinned_image_is_pinned():
    text = "FROM python:3.11-slim@sha256:" + "0" * 64 + "\n"
    assert lint(text) == []
    # A digest pins content even when the tag says latest.
    text = "FROM python:latest@sha256:" + "0" * 64 + "\n"
    assert lint(text) == []


def test_cd_and_sudo_flagged_only_as_commands():
    bad = "RUN cd /opt && sudo make install\n"
    assert pairs(lint(bad)) == [(1, "DL3003"), (1, "DL3004")]
    # Quoted text and non-command positions are not shell commands.
    good = 'RUN echo "cd /tmp is fine" && echo sudo && ls\n'
    assert lint(good) == []


def test_upgrade_and_apt_install_rules():
    text = "RUN apt-get update && apt-get install -y curl\n"
    assert pairs(lint(text)) == [(1, "DL3009"), (1, "DL3015")]
    text = (
        "RUN apt-get update && apt-get install -y --no-install-recommends curl"
        " && rm -rf /var/lib/apt/lists/*\n"
    )
    assert lint(text) == []
    text = "RUN apt-get dist-upgrade -y\n"
    assert pairs(lint(text)) == [(1, "DL3005")]


def test_add_rules():
    assert pairs(lint("ADD app /opt/app\n")) == [(1, "DL3020")]
    assert lint("ADD app.tar.gz /opt/\n") == []
    assert lint("ADD https://example.com/app.tar.gz /opt/\n") == []
    assert lint("COPY app /opt/app\n") == []


def test_copy_before_dependency_install_busts_cache():
    text = "COPY . .\nRUN pip install -r requirements.txt\n"
    assert pairs(lint(text)) == [(1, "C1001")]
    text = "COPY . .\nRUN npm ci\n"
    assert pairs(lint(text)) == [(1, "C1001")]
    # Manifest-first order keeps the dependency layer cached.
    text = (
        "COPY package.json package-lock.json ./\n"
        "RUN npm ci\n"
        "COPY . .\n"
        "RUN npm run build\n"
    )
    assert lint(text) == []
    # Installing the app itself has no manifest to hoist: not flagged.
    text = "COPY . .\nRUN pip install --no-cache-dir .\n"
    assert lint(text) == []


def test_secret_shaped_env_keys():
    assert pairs(lint("ENV NPM_TOKEN=abc\n")) == [(1, "C1002")]
    assert pairs(lint("ARG OPENAI_API_KEY\n")) == [(1, "C1002")]
    assert pairs(lint("ENV NPM_TOKEN abc\n")) == [(1, "C1002")]
    assert lint("ENV TOKENIZER_PARALLELISM=false\n") == []
    assert lint("ENV APP_PORT=8080\n") == []


def test_continuation_lines_report_start_line():
    text = (
        "RUN apt-get update && \\\n"
        "    apt-get install -y \\\n"
        "    curl\n"
    )
    assert pairs(lint(text)) == [(1, "DL3009"), (1, "DL3015")]


def test_format_findings_shape():
    formatted = format_findings(lint(BAD_DOCKERFILE))
    assert all(line.startswith("L") for line in formatted)
    assert formatted[0] == "L2 [DL3007] image 'ubuntu' uses the :latest tag; pin an explicit version"
    assert len(formatted) == len(BAD_EXPECTED)


def test_lint_service_wiring():
    """/lint and /optimize report through lint_service()."""
    os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")
    sys.path.insert(0, str(BACKEND_DIR))
    from main import lint_service

    results = lint_service(BAD_DOCKERFILE)
    assert results == format_findings(lint(BAD_DOCKERFILE))
    assert lint_service("FROM python:3.12-slim-bookworm\n") == []
