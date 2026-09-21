#!/usr/bin/env bash
# Installs Docker Engine + Compose v2 inside WSL Ubuntu (no Docker Desktop).
# Run as root:  wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Users/Pouya/Desktop/PROJECTS/mamad/deploy/wsl-docker-setup.sh <linux-username>
set -euo pipefail

LINUX_USER="${1:?usage: wsl-docker-setup.sh <linux-username>}"

# Docker in WSL needs systemd to run as a service.
if ! grep -q "systemd=true" /etc/wsl.conf 2>/dev/null; then
	printf '[boot]\nsystemd=true\n' >> /etc/wsl.conf
	echo "systemd enabled in /etc/wsl.conf -> run 'wsl --shutdown' in Windows, then run this script again."
	exit 0
fi

# Install from Docker's official apt repo (get.docker.com is unreachable from some networks).
if ! command -v docker >/dev/null 2>&1; then
	apt-get update
	apt-get install -y ca-certificates curl
	install -m 0755 -d /etc/apt/keyrings
	curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
	chmod a+r /etc/apt/keyrings/docker.asc
	. /etc/os-release
	echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME:-$VERSION_CODENAME} stable" \
		> /etc/apt/sources.list.d/docker.list
	apt-get update
	apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi

usermod -aG docker "$LINUX_USER"
systemctl enable --now docker

docker version --format 'docker {{.Server.Version}}'
docker compose version
echo "Done. Close and reopen the Ubuntu terminal so '$LINUX_USER' can use docker without sudo."
