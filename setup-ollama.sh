#!/usr/bin/env bash
# Run in a terminal so Omarchy can request the system password if needed.
set -euo pipefail
versework_model="${1:-qwen3:8b}"
if [[ "$versework_model" == *cloud* || "$versework_model" == -* ]]; then
  echo 'Choose a local Ollama model name.'
  exit 1
fi
if ! command -v omarchy >/dev/null; then
  echo 'This setup script requires Omarchy. Install Ollama for your distribution, then pull a local model.'
  exit 1
fi
# Omarchy handles privilege elevation and installs only missing packages.
omarchy pkg add ollama ollama-vulkan
export OLLAMA_HOST=127.0.0.1:11434
export OLLAMA_NO_CLOUD=1
export OLLAMA_VULKAN=1
versework_data="${VERSEWORK_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/versework/data}"
mkdir -p -- "$versework_data"
if ! curl --noproxy '*' --fail --silent http://127.0.0.1:11434/api/tags >/dev/null; then
  nohup ollama serve >>"$versework_data/ollama.log" 2>&1 </dev/null &
  versework_ready=0
  for ((versework_attempt=0; versework_attempt<30; versework_attempt++)); do
    if curl --noproxy '*' --fail --silent http://127.0.0.1:11434/api/tags >/dev/null; then
      versework_ready=1
      break
    fi
    sleep 1
  done
  if ((versework_ready == 0)); then
    echo "Ollama could not start. See $versework_data/ollama.log"
    exit 1
  fi
fi
echo "Downloading $versework_model. The default Qwen3 8B download is approximately 5 GB."
ollama pull "$versework_model"
echo 'Ollama is ready. Open Versework → Settings → Check connection, select the model, and Save settings.'
