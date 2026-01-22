import io
import os
import sys
import tarfile
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set

import docker
import docker.errors

# Embedded assets
AGENT_ENTRYPOINT_SH = """#!/bin/bash
if [ $# -eq 0 ]; then
  exec /bin/bash --login -i
else
  exec /bin/bash --login -c "$*"
fi
"""

# Constants
IMAGE_REPOSITORY = "mheap/agent-en-place"
OPENCODE_CONFIG_DIR = ".config/opencode/"
OPENCODE_SHARE_DIR = ".local/share/opencode"

log = logging.getLogger(__name__)

class ToolSpec:
    def __init__(self, name: str, version: str):
        self.name = name.lower()
        self.version = version

class ConfigFile:
    def __init__(self, path: Path, rel_path: str):
        self.path = path
        self.rel_path = rel_path
        self.content = path.read_bytes()

def sanitize_tag_component(value: str) -> str:
    value = value.lower().strip()
    result = []
    last_hyphen = False
    for char in value:
        if char.isalnum():
            result.append(char)
            last_hyphen = False
        elif char == '.':
            result.append('.')
            last_hyphen = False
        elif char in '+@:/_-':
            if not last_hyphen:
                result.append('-')
                last_hyphen = True
    return "".join(result).strip('-')

def detect_tools(cwd: Path) -> Tuple[List[ToolSpec], List[ConfigFile]]:
    """
    Scans the current directory for tool configuration files.
    Returns a list of detected tools and a list of files to be included in the build context.
    """
    specs: List[ToolSpec] = []
    files_to_copy: List[ConfigFile] = []
    seen_tools: Set[str] = set()

    # 1. .tool-versions (asdf/mise)
    tool_versions_path = cwd / ".tool-versions"
    if tool_versions_path.exists():
        files_to_copy.append(ConfigFile(tool_versions_path, ".tool-versions"))
        content = tool_versions_path.read_text()
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                version = parts[1]
                specs.append(ToolSpec(name, version))
                seen_tools.add(name)

    # 2. mise.toml
    mise_toml_path = cwd / "mise.toml"
    if mise_toml_path.exists():
        files_to_copy.append(ConfigFile(mise_toml_path, "mise.toml"))
        # Basic TOML parsing for [tools] section
        # We'll use a simple parser to avoid extra dependencies if possible, 
        # but since we can't assume 'tomllib' (Python 3.11+), we'll do basic line parsing 
        # similar to the Go implementation.
        content = mise_toml_path.read_text()
        in_tools = False
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if line.startswith('[tools]'):
                in_tools = True
                continue
            elif line.startswith('[') and line != '[tools]':
                in_tools = False
                continue
            
            if in_tools and '=' in line:
                key, val = line.split('=', 1)
                key = key.strip().strip('"\'')
                val = val.strip().strip('"\'')
                if key and val:
                    specs.append(ToolSpec(key, val))
                    seen_tools.add(key)

    # 3. Idiomatic files
    idiomatic_map = {
        "node": [".nvmrc", ".node-version"],
        "python": [".python-version", ".python-versions"],
        "ruby": [".ruby-version", "Gemfile"],
        "go": [".go-version"],
        "java": [".java-version", ".sdkmanrc"],
        "crystal": [".crystal-version"],
        "elixir": [".exenv-version"],
        "yarn": [".yvmrc"]
    }

    for tool, filenames in idiomatic_map.items():
        if tool in seen_tools:
            continue
        
        for filename in filenames:
            file_path = cwd / filename
            if file_path.exists():
                version = None
                
                # Simple one-line readers
                if filename == "Gemfile":
                    # Go implementation looked for 'ruby "3.3.0"'
                    content = file_path.read_text()
                    for line in content.splitlines():
                        if line.strip().startswith('ruby '):
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                version = parts[1].strip('"\'')
                                break
                elif filename == ".sdkmanrc":
                    content = file_path.read_text()
                    for line in content.splitlines():
                        if line.strip().startswith('java='):
                            version = line.strip().split('=', 1)[1]
                            break
                else:
                    # Read first line
                    content = file_path.read_text().strip()
                    if content:
                        version = content.splitlines()[0].strip()

                if version:
                    specs.append(ToolSpec(tool, version))
                    files_to_copy.append(ConfigFile(file_path, filename))
                    seen_tools.add(tool)
                    break 

    # Ensure Node exists (Opencode/Copilot often require it)
    if "node" not in seen_tools:
        specs.append(ToolSpec("node", "latest"))

    # Ensure Opencode exists in tool list
    if "npm:opencode-ai" not in seen_tools:
         specs.append(ToolSpec("npm:opencode-ai", "latest"))

    return specs, files_to_copy

def generate_dockerfile(specs: List[ToolSpec], files: List[ConfigFile]) -> str:
    packages = ["curl", "ca-certificates", "gnupg", "apt-transport-https", "libatomic1"]
    
    dockerfile = []
    dockerfile.append("FROM debian:12-slim")
    dockerfile.append("")
    dockerfile.append("RUN apt-get update && apt-get install -y --no-install-recommends " + " ".join(packages))
    dockerfile.append("")
    dockerfile.append("RUN install -dm 755 /etc/apt/keyrings")
    dockerfile.append("RUN curl -fSs https://mise.jdx.dev/gpg-key.pub | tee /etc/apt/keyrings/mise-archive-keyring.pub >/dev/null")
    dockerfile.append('RUN arch=$(dpkg --print-architecture) && echo "deb [signed-by=/etc/apt/keyrings/mise-archive-keyring.pub arch=$arch] https://mise.jdx.dev/deb stable main" | tee /etc/apt/sources.list.d/mise.list')
    dockerfile.append("RUN apt-get update && apt-get install -y mise")
    dockerfile.append("RUN rm -rf /var/lib/apt/lists/*")
    dockerfile.append("")
    dockerfile.append("RUN groupadd -r agent && useradd -m -r -u 1000 -g agent -s /bin/bash agent")
    dockerfile.append("ENV HOME=/home/agent")
    dockerfile.append('ENV PATH="/home/agent/.local/share/mise/shims:/home/agent/.local/bin:${PATH}"')
    dockerfile.append("")
    dockerfile.append("RUN mkdir -p /home/agent/.config/mise")
    
    # Labels
    for spec in specs:
        key = f"com.mheap.agent-en-place.{sanitize_tag_component(spec.name)}"
        val = sanitize_tag_component(spec.version)
        dockerfile.append(f'LABEL {key}="{val}"')
    
    dockerfile.append("WORKDIR /home/agent")
    
    # Copy files
    has_mise_toml = False
    for f in files:
        dockerfile.append(f"COPY {f.rel_path} {f.rel_path}")
        if f.rel_path == "mise.toml":
            has_mise_toml = True
            
    if has_mise_toml:
        dockerfile.append("COPY mise.toml /home/agent/.config/mise/config.toml")
    else:
        # Generate mise.toml content if not present
        dockerfile.append("RUN printf '%s\\n' \\")
        dockerfile.append("  '[tools]' \\")
        for spec in specs:
            # We skip 'npm:opencode-ai' here if we were doing the exact Go logic, 
            # but standardizing on just writing all detected specs is safer for a port.
            # The Go logic had some complex deduping/renaming logic for 'idiomatic' vs 'mise'.
            # We'll use the spec list we built.
            dockerfile.append(f"  '{spec.name}' = '{spec.version}' \\")
        dockerfile.append("  > /home/agent/.config/mise/config.toml")

    # Chown
    chown_files = [f.rel_path for f in files]
    chown_files.append("/home/agent/.config/mise/config.toml")
    dockerfile.append(f"RUN chown agent:agent {' '.join(chown_files)}")

    dockerfile.append("COPY assets/agent-entrypoint.sh /usr/local/bin/agent-entrypoint")
    dockerfile.append("RUN chmod +x /usr/local/bin/agent-entrypoint")
    
    dockerfile.append("USER agent")
    dockerfile.append("RUN mise trust")
    dockerfile.append("RUN mise install")
    dockerfile.append("RUN printf 'export PATH=\"/home/agent/.local/share/mise/shims:/home/agent/.local/bin:$PATH\"\\n' > /home/agent/.bashrc")
    dockerfile.append("RUN printf 'source ~/.bashrc\\n' > /home/agent/.bash_profile")
    dockerfile.append("WORKDIR /workdir")
    dockerfile.append('ENTRYPOINT ["/bin/bash", "/usr/local/bin/agent-entrypoint"]')

    return "\n".join(dockerfile)

def build_image_name(specs: List[ToolSpec]) -> str:
    parts = []
    # Deduplicate based on name for the tag
    seen = set()
    sorted_specs = sorted(specs, key=lambda s: s.name)
    
    for spec in sorted_specs:
        name = sanitize_tag_component(spec.name)
        if not name or name in seen:
            continue
        seen.add(name)
        
        version = sanitize_tag_component(spec.version)
        if not version:
            version = "latest"
        parts.append(f"{name}-{version}")
        
    if not parts:
        return f"{IMAGE_REPOSITORY}:latest"
    
    return f"{IMAGE_REPOSITORY}:{'-'.join(parts)}"

def run_agent(cwd: Path, debug: bool = False, rebuild: bool = False, dockerfile_only: bool = False):
    specs, files = detect_tools(cwd)
    dockerfile_content = generate_dockerfile(specs, files)
    
    if dockerfile_only:
        print(dockerfile_content)
        return

    client = docker.from_env()

    image_name = build_image_name(specs)
    log.info(f"Target Image: {image_name}")

    # Check if image exists
    needs_build = rebuild
    if not needs_build:
        try:
            client.images.get(image_name)
        except docker.errors.ImageNotFound:
            needs_build = True

    if needs_build:
        log.info("Building image...")
        # Create build context
        f = io.BytesIO()
        with tarfile.open(fileobj=f, mode='w') as tar:
            # Add Dockerfile
            df_bytes = dockerfile_content.encode('utf-8')
            tar_info = tarfile.TarInfo(name='Dockerfile')
            tar_info.size = len(df_bytes)
            tar.addfile(tar_info, io.BytesIO(df_bytes))
            
            # Add Entrypoint
            ep_bytes = AGENT_ENTRYPOINT_SH.encode('utf-8')
            tar_info = tarfile.TarInfo(name='assets/agent-entrypoint.sh')
            tar_info.size = len(ep_bytes)
            tar_info.mode = 0o755
            tar.addfile(tar_info, io.BytesIO(ep_bytes))
            
            # Add Config Files
            for config_file in files:
                tar_info = tarfile.TarInfo(name=config_file.rel_path)
                tar_info.size = len(config_file.content)
                tar.addfile(tar_info, io.BytesIO(config_file.content))
        
        f.seek(0)
        
        # Build
        try:
            # If debug is true, we stream the output
            # docker-py build returns a generator of JSON objects
            resp = client.api.build(
                fileobj=f,
                custom_context=True,
                tag=image_name,
                rm=True,
                forcerm=True,
                pull=True,
                decode=True
            )
            for chunk in resp:
                if 'stream' in chunk:
                    msg = chunk['stream'].strip()
                    if msg:
                        if debug:
                            print(msg)
                        else:
                            log.debug(msg)
                elif 'error' in chunk:
                    raise docker.errors.BuildError(chunk['error'], chunk.get('errorDetail'))
                    
        except docker.errors.BuildError as e:
            log.error(f"Build failed: {e}")
            sys.exit(1)

    # Prepare Run Command
    home = Path.home()
    
    # Config mounts
    volumes = {
        str(cwd): {'bind': '/workdir', 'mode': 'rw'},
    }
    
    # Opencode specific mounts
    config_src = home / ".config/opencode"
    if config_src.exists():
         volumes[str(config_src)] = {'bind': '/home/agent/.config/opencode/', 'mode': 'rw'}
         
    share_src = home / ".local/share/opencode"
    if share_src.exists():
        volumes[str(share_src)] = {'bind': '/home/agent/.local/share/opencode', 'mode': 'rw'}

    cmd_str = f"docker run --rm -it {' '.join([f'-v {k}:{v['bind']}' for k,v in volumes.items()])} {image_name} opencode"
    print(cmd_str)
