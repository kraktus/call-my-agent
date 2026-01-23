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
    return ''.join(random.choices(string.ascii_lowercase, k=length))

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
    res = run(
        ["docker", "images", "-q", IMAGE_NAME], check=False
    )
    return bool(res.stdout.strip())

def run_container(cwd: Path) -> None:
    container_name = f"call-my-agent-{random_string(5)}"
    run(
        [
            "docker",
            "run",
            "--rm",  # Always remove after execution
            "--name",
            container_name,
            "-it"
        ],
        check=False,
    )
    log.info(f"container {container_name} stopped.")

def main(cwd: Path, debug: bool = False, rebuild: bool = False, dockerfile_only: bool = False):
    if not image_already_exists():
        build_image()

    
    # Config mounts
    volumes = {
        str(cwd): {'bind': '/workdir', 'mode': 'rw'},
    }
    
    # Opencode specific mounts
    config_src = HOME / ".config/opencode"
    if config_src.exists():
         volumes[str(config_src)] = {'bind': '/home/agent/.config/opencode/', 'mode': 'rw'}
         
    share_src = HOME / ".local/share/opencode"
    if share_src.exists():
        volumes[str(share_src)] = {'bind': '/home/agent/.local/share/opencode', 'mode': 'rw'}

    cmd_str = f"docker run --rm -it {' '.join([f'-v {k}:{v['bind']}' for k,v in volumes.items()])} {IMAGE_NAME} opencode"
    print(cmd_str)
    # Actually run it
    # We need to parse the volume args properly for the list-based run command
    docker_cmd = ["docker", "run", "--rm", "-it"]
    for k, v in volumes.items():
        docker_cmd.extend(["-v", f"{k}:{v['bind']}"])
    docker_cmd.extend([IMAGE_NAME, "opencode"])
    
    run(docker_cmd, check=False)
