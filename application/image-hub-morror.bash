mkdir -p /etc/containerd/certs.d/{docker.io,ghcr.io,mcr.microsoft.com,quay.io,registry.k8s.io}

# Docker Hub
tee /etc/containerd/certs.d/docker.io/hosts.toml <<'EOF'
server = "https://docker.io"

[host."https://docker-mirror.liara.ir"]
  capabilities = ["pull", "resolve"]
EOF

# GitHub Container Registry
tee /etc/containerd/certs.d/ghcr.io/hosts.toml <<'EOF'
server = "https://ghcr.io"

[host."https://ghcr-mirror.liara.ir"]
  capabilities = ["pull", "resolve"]
EOF

# Microsoft Container Registry
tee /etc/containerd/certs.d/mcr.microsoft.com/hosts.toml <<'EOF'
server = "https://mcr.microsoft.com"

[host."https://mcr-mirror.liara.ir"]
  capabilities = ["pull", "resolve"]
EOF

# Quay
tee /etc/containerd/certs.d/quay.io/hosts.toml <<'EOF'
server = "https://quay.io"

[host."https://quay-mirror.liara.ir"]
  capabilities = ["pull", "resolve"]
EOF

# Kubernetes registry
tee /etc/containerd/certs.d/registry.k8s.io/hosts.toml <<'EOF'
server = "https://registry.k8s.io"

[host."https://k8s-mirror.liara.ir"]
  capabilities = ["pull", "resolve"]
EOF


grep -n -A5 'registry' /etc/containerd/config.toml

systemctl restart containerd