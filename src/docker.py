#!/usr/bin/python3
#
# coding: utf-8
# Licence: GNU AGPLv3

""""""

import io
import os
import sys
import tarfile
import logging
from pathlib import Path
import subprocess
import random
from dataclasses import dataclass
import string
from typing import Dict, List, Optional, Tuple, Set, Any

from . import REPO_DIR, log, HOME

# Constants
IMAGE_NAME = "kraktus/call-my-agent"
OPENCODE_CONFIG_DIR = ".config/opencode/"
OPENCODE_SHARE_DIR = ".local/share/opencode"


def run(
    cmd: List[str], check: bool = True, *args: Any, **kwargs: Any
) -> subprocess.CompletedProcess[Any]:
    """
    Executes a shell command, checks for success, and returns its stdout.

    Args:
        args: A list of strings representing the command and its arguments.

    Raises:
        subprocess.CalledProcessError: If the command returns a non-zero exit code.
    """
    log.debug(f"Running command: {' '.join(cmd)}")
    res = subprocess.run(cmd, *args, check=check, text=True, **kwargs)
    return res


def random_string(length: int):
    return "".join(random.choices(string.ascii_lowercase, k=length))


def build_image():
    run(
        [
            "docker",
            "build",
            "-f",
            str(REPO_DIR / "Dockerfile"),
            str(REPO_DIR),
            "-t",
            IMAGE_NAME,
        ]
    )
    log.info(f"Builf of {IMAGE_NAME} successful")


def image_already_exists() -> bool:
    res = run(["docker", "images", "-q", IMAGE_NAME], check=False)
    return bool(res.stdout.strip())


@dataclass(frozen=True)
class Bind:
    source: Path
    target: Path
    readonly: bool = False

    def to_docker_arg(self) -> str:
        return f"--mount type=bind,src={self.source},dst={self.target}{',readonly' if self.readonly else ''}"


# we're reinvinting the docker package...
def run_container(cwd: Path, binds: list[Bind]) -> None:
    container_name = f"call-my-agent-{random_string(5)}"
    run(
        [
            "docker",
            "run",
            "--rm",  # Always remove after execution
            "--name",
            container_name,
            *[bind.to_docker_arg() for bind in binds],
            "-it",
            "-t",
            IMAGE_NAME,
        ],
        check=False,
    )
    log.info(f"container {container_name} stopped.")


def main(
    cwd: Path, debug: bool = False, rebuild: bool = False, dockerfile_only: bool = False
):
    if not image_already_exists():
        build_image()

    # Config mounts
    binds = [Bind(source=cwd, target=Path("/workdir"))]

    # Opencode specific mounts
    config_src = HOME / ".config/opencode"
    if config_src.exists():
        binds.append(
            Bind(source=config_src, target=Path("/home/agent/.config/opencode/"))
        )

    share_src = HOME / ".local/share/opencode"
    if share_src.exists():
        binds.append(
            Bind(source=share_src, target=Path("/home/agent/.local/share/opencode/"))
        )

    run_container(cwd=cwd, binds=binds)
