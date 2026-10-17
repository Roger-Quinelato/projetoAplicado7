#!/usr/bin/env bash
# Instala o cliente (wrapper) do ai-memory em Linux/macOS/WSL2 e conecta o Claude Code.
# Pré-requisito: Docker em execução (no WSL2, ative a integração da distro no Docker Desktop).
# Execute a partir desta pasta:  bash instalar-wsl.sh
# Fonte: https://github.com/akitaonrails/ai-memory/blob/main/docs/windows.md
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Instalar o wrapper com verificação de checksum
mkdir -p ~/.local/bin
wrapper_base=https://github.com/akitaonrails/ai-memory/releases/latest/download/ai-memory-wrapper
wrapper_tmp="$(mktemp -d)"
trap 'rm -rf "$wrapper_tmp"' EXIT
curl -fsSL "$wrapper_base" -o "$wrapper_tmp/ai-memory-wrapper"
curl -fsSL "$wrapper_base.sha256" -o "$wrapper_tmp/ai-memory-wrapper.sha256"
(cd "$wrapper_tmp" && sha256sum -c ai-memory-wrapper.sha256)
install -m 0755 "$wrapper_tmp/ai-memory-wrapper" ~/.local/bin/ai-memory
export PATH="$HOME/.local/bin:$PATH"

# 2. Subir o servidor (container). Não rode também `ai-memory serve`.
docker compose -f "$SCRIPT_DIR/docker-compose.yml" up -d

# 3. Verificar e conectar o Claude Code
ai-memory status
ai-memory install-mcp --client claude-code --apply
ai-memory install-hooks --agent claude-code --apply

echo "Pronto. Inicie o Claude Code de dentro do WSL2 e verifique com a ferramenta memory_status."
echo "Se ~/.local/bin não estiver no PATH, adicione: export PATH=\"\$HOME/.local/bin:\$PATH\""
