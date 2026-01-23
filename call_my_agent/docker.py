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
from itertools import chain
import string
from typing import Dict, List, Optional, Tuple, Set, Any

from . import REPO_DIR, log, HOME

# Constants
IMAGE_NAME = "kraktus/call-my-agent"
OPENCODE_CONFIG_DIR = ".config/opencode/"
OPENCODE_SHARE_DIR = ".local/share/opencode"

CONTAINER_HOME = Path("/home/linuxbrew")


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
    log.info(f"Building Docker image {IMAGE_NAME}...")
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
    return res != ""


@dataclass(frozen=True)
class Bind:
    source: Path
    target: Path
    readonly: bool = False

    def to_docker_arg(self) -> list[str]:
        # target is in the container so obviously cannot exist here
        return [f"--mount" ,f"type=bind,src={str(self.source.resolve(strict=True))},dst={str(self.target)}{',readonly' if self.readonly else ''}"]


# we're reinvinting the docker package...
def run_container(cwd: Path, binds: list[Bind], agent_args: list[str]) -> None:
    container_name = f"call-my-agent-{random_string(5)}"
    binds_args = list(chain.from_iterable(bind.to_docker_arg() for bind in binds))
    print(binds_args)
    run(
        [
            "docker",
            "run",
            "--rm",  # Always remove after execution
            "--name",
            container_name,
            "-it",
            *binds_args,
            IMAGE_NAME,
            *agent_args
        ],
        check=False,
    )
    log.info(f"container {container_name} stopped.")


def run_agent(
    cwd: Path, agent_args: list[str] | None, rebuild: bool = False):
    if agent_args is None:
        agent_args = []
    if rebuild or not image_already_exists():
        build_image()
    else:
        log.info(f"Using existing image {IMAGE_NAME}")

    # Config mounts
    binds = [Bind(source=cwd, target=CONTAINER_HOME)]

    # Opencode specific mounts
    config_src = HOME / ".config/opencode"
    if config_src.exists():
        binds.append(
            Bind(source=config_src, target=Path(CONTAINER_HOME / ".config/opencode/"))
        )

    share_src = HOME / ".local/share/opencode"
    if share_src.exists():
        binds.append(
            Bind(source=share_src, target=Path(CONTAINER_HOME / ".local/share/opencode/"))
        )

    run_container(cwd=cwd, binds=binds,agent_args=agent_args)
