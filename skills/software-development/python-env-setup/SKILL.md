---
name: python-env-setup
description: Python environment setup — conda/miniconda installation, environment creation, mirror configuration, and activation patterns.
tags: [setup, python, conda, miniconda, environment, mirrors]
---

# Python Environment Setup

Conda-based Python environment provisioning: install Miniconda, create environments, configure mirrors, and handle activation in scripted contexts.

## When to Use

- User asks to create a Python/conda environment
- `conda` or `python` commands fail with "command not found"
- Need to configure domestic mirrors for faster package installs
- Setting up a fresh development environment on WSL/Linux

## Miniconda Installation

```bash
# Download installer
cd /tmp && curl -fsSL -o miniconda.sh https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

# Silent install to ~/miniconda3
bash /tmp/miniconda.sh -b -p $HOME/miniconda3

# Initialize for bash
~/miniconda3/bin/conda init bash

# Accept Terms of Service (conda 26.x+) — REQUIRED before creating environments
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
```

## Environment Creation

```bash
# Activate conda in the current shell (non-login / scripted context)
eval "$($HOME/miniconda3/bin/conda shell.bash hook)"

# Create environment
conda create -y -n <env_name> python=<version>

# Verify
conda activate <env_name> && python --version && which python
```

## Non-Interactive Activation

`conda activate` does NOT work in non-login shells even after `conda init bash`. Always use:

```bash
eval "$($HOME/miniconda3/bin/conda shell.bash hook)" && conda activate <env_name>
```

This is the pattern for all scripted terminal commands — `source ~/.bashrc` is unreliable in non-interactive contexts.

## Chinese Mirror Configuration

### Conda channels (Tsinghua)

```bash
conda config --set show_channel_urls yes
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge/
```

### Pip (Tsinghua)

```bash
mkdir -p ~/.config/pip
cat > ~/.config/pip/pip.conf << 'EOF'
[global]
index-url = https://pypi.tuna.tsinghua.edu.cn/simple
trusted-host = pypi.tuna.tsinghua.edu.cn
EOF
```

## Pitfalls

### Conda 26.x TOS Requirement

Conda 26+ requires explicit Terms of Service acceptance before `conda create` works. Without it, the command prints a TOS message and exits — the environment is NOT created, but the exit code may still be 0. Always run `conda tos accept` for both `pkgs/main` and `pkgs/r` channels first.

### Conda Activate in Scripted Contexts

`conda init bash` modifies `~/.bashrc`, but that file is only sourced in interactive login shells. In non-interactive contexts (background processes, subshells, CI), use the `eval "$(conda shell.bash hook)"` pattern. `source ~/.bashrc` in a script is unreliable because many `.bashrc` files have early `return`/`exit` guards for non-interactive shells.

### Mirror Channel Order

Conda uses channels in reverse order of addition (last added = highest priority). Add `conda-forge` last if you want it to take priority over `pkgs/main`. For most users, the default priority order (main → free → conda-forge) is fine.
