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


###########
# Classes #
###########


@dataclass(frozen=True)
class Bind:
    source: Path
    target: Path
    readonly: bool = False

    def to_docker_arg(self) -> list[str]:
        # target is in the container so obviously cannot exist here
        return [
            f"--mount",
            f"type=bind,src={str(self.source.resolve(strict=True))},dst={str(self.target)}{',readonly' if self.readonly else ''}",
        ]


@dataclass(frozen=True)
class MountPath:
    src: Path
    target: Path

    @classmethod
    def from_home_path(cls, path: str) -> "MountPath":
        return cls(src=Path(HOME / path), target=Path(CONTAINER_HOME / path))

    def to_bind_if_exists(self) -> Optional[Bind]:
        if self.src.exists():
            return Bind(source=self.src, target=self.target)
        else:
            return None

    def make_dir(self) -> str:
        return f"mkdir -p {str(self.target)}"



#############
# Functions #
#############


def join_but_not_last(lst: list[str], sep: str) -> str:
    if len(lst) == 0:
        return ""
    elif len(lst) == 1:
        return lst[0]
    else:
        return sep.join(lst[:-1]) + sep + lst[-1]

def to_dockerfile(dirs_to_mount: list[MountPath]) -> str:
    brewfile_path = CONTAINER_HOME / ".Brewfile"
    return f"""FROM homebrew/brew:latest

    ARG UID=501
    ARG GID=20

    USER root

    RUN usermod -u $UID linuxbrew && usermod -aG 20 linuxbrew

    USER linuxbrew

    # Install dependencies from Brewfile
    COPY Brewfile {brewfile_path}
    RUN brew bundle install --file {brewfile_path}

    # Needed because otherwise the intermediate directories are owned by root and the agent user can't write to them
    RUN {join_but_not_last([p.make_dir() for p in dirs_to_mount], " \\ && ")}

    COPY assets/agent-entrypoint.sh {CONTAINER_HOME}/agent-entrypoint.sh
    # home of the user
    WORKDIR {CONTAINER_HOME}/workdir

    ENTRYPOINT ["{CONTAINER_HOME}/agent-entrypoint.sh"]
    CMD ["opencode"]
    """


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


def build_image(uid: int, gid: int, dockerfile: str):
    log.info(f"Building Docker image {IMAGE_NAME} with u:{uid} g:{gid}...")
    run(
        [
            "docker",
            "build",
            "--build-arg",
            f"UID={uid}",
            "--build-arg",
            f"GID={gid}",
            "-f",
            "-",
            str(REPO_DIR),
            "-t",
            IMAGE_NAME,
        ],
        input=dockerfile,
    )
    log.info(f"Builf of {IMAGE_NAME} successful")


def image_already_exists() -> bool:
    res = run(["docker", "images", "-q", IMAGE_NAME], check=False)
    return res != ""


# we're reinvinting the docker package...
def run_container(binds: list[Bind], agent_args: list[str]) -> None:
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
            *agent_args,
        ],
        check=False,
    )
    log.info(f"container {container_name} stopped.")


def run_agent(
    cwd: Path, uid: int, gid: int, agent_args: list[str] | None, rebuild: bool = False
):

    mount_paths = [
        MountPath.from_home_path(x) for x in [".config/opencode", ".local/share/opencode"]
    ]
    if agent_args is None:
        agent_args = []
    if rebuild or not image_already_exists():
        build_image(uid=uid, gid=gid, dockerfile=to_dockerfile(mount_paths))
    else:
        log.info(f"Using existing image {IMAGE_NAME}")

    # Config mounts
    binds = [Bind(source=cwd, target=CONTAINER_HOME / "workdir")]
    for path in mount_paths:
        if target := path.to_bind_if_exists():
            binds.append(target)

    run_container(binds=binds, agent_args=agent_args)
