# Versework — Omarchy Song Creator

A native GTK 4 desktop app for writing a song or an EP with a **local Ollama model**, reviewing the drafts, and preparing lyrics and settings to paste into Suno. No Suno API, cloud LLM account, browser server, or Python packages from pip are required.

## Install on Omarchy

```bash
git clone https://github.com/Ashcutus/Omarchy-Song-Creator.git
cd Omarchy-Song-Creator
./install.sh
./setup-ollama.sh
```

`install.sh` installs the app for the current user and adds **Versework — Song Creator** to the desktop launcher. GTK 4 and Python GObject are normally already installed on Omarchy. If they are missing:

```bash
omarchy pkg add python-gobject gtk4
```

`setup-ollama.sh` uses `omarchy pkg add ollama ollama-vulkan`, starts a local Ollama server, and downloads **qwen3:8b** (approximately 5 GB). It may ask for your system password when installing packages. Model inference may use substantial RAM/VRAM. The Vulkan backend supports compatible GPUs; actual acceleration depends on the installed driver and Ollama build.

You may select another local model:

```bash
./setup-ollama.sh qwen3:4b
```

Then open the app, choose **Settings → Check connection**, select the installed model, and **Save settings**. If Ollama is not running after a restart, use **Settings → Start Ollama**. The app does not add a system service or start a model download without the setup command.

To run directly without installing the launcher:

```bash
./launch.sh
```

## Workflow

1. Create a project with a name, style prompt, song count, target duration range in seconds, and maximum AI rewrites per song. Add a language and optional theme.
2. Select **Write remaining drafts**, or write a single track. Each track uses the project brief and context from already written tracks to build a cohesive collection.
3. Review and edit each of the eight fields: **song title, lyrics, style prompt, exclusions, vocal gender, weirdness %, style influence %, variety level**. Variety supports `off`, `normal`, `high`, `extra`, and `max`.
4. Copy fields into Suno and generate the audio there. Bring listening notes back into Versework as feedback.
5. Lock any fields that must remain exactly unchanged. Request a rewrite for a single track, or apply EP feedback to selected eligible tracks.
6. Approve songs when you are happy. Export the EP as readable Markdown and a JSON project backup containing the complete version history.

Target duration guides lyrics and arrangement; it does not guarantee the duration of audio generated in Suno. Vocal options are writing metadata (male, female, mixed, unspecified, or instrumental). Match those to the controls available in your version of Suno.

### Revision rules

- An initial draft does **not** use a rewrite.
- Only a successfully validated and saved AI revision increments the per-song counter.
- Manual edits and restoring a previous version do not use a rewrite, and never reset the counter.
- Approved songs cannot be edited, rewritten or restored until explicitly reopened.
- At the rewrite limit, a song remains **Limit reached · review needed** until the user approves it. It is not automatically marked finished.
- Field locks are enforced by the app, not merely requested in the prompt.
- Completed songs are saved as an EP is generated. A failed later song does not discard earlier work; use **Write remaining drafts** to resume.
- Stop writing cancels at the next streamed response from Ollama; an initial model load may delay cancellation. Closing the app preserves previously saved drafts.

## Local storage and privacy

Projects and settings live in `~/.local/share/versework/data/projects.sqlite3`, using SQLite transactions. Drafts are saved on generation, editing/navigation, and close. Exported JSON includes versions, feedback and the original creative brief. The current app exports backups but does not yet provide a JSON backup importer; keep the SQLite database for full app-state restoration.

The app only connects to `http://127.0.0.1:11434`, bypasses HTTP proxies, and excludes models advertised as cloud/remote. Its Ollama startup sets `OLLAMA_NO_CLOUD=1`. The model download requires internet access; writing uses the installed local model. No Suno requests or automatic audio generation occur.

Installed application files: `~/.local/share/versework/app/`.
Desktop launcher: `~/.local/share/applications/io.versework.Studio.desktop`.
An Ollama process started by the app logs to `~/.local/share/versework/data/ollama.log` and may remain running after Versework closes.

Run `./install.sh` again after updating the repository to update the installed app without replacing your project database.

## Development and validation

Python 3, GTK 4, and PyGObject are the only app dependencies. Ollama is accessed using its documented streaming `/api/generate` API with a JSON schema and local validation.

```bash
python -m unittest discover -v
python -m py_compile app.py core.py
bash -n install.sh launch.sh setup-ollama.sh
```

Tests cover revision limits, approval protection, field locks, restoration, restart persistence, prompt context, exports, local model filtering and streamed response validation/cancellation. A GUI smoke fixture can be run on a display using an isolated data directory:

```bash
VERSEWORK_DATA=/tmp/versework-smoke ./launch.sh --smoke
```

This creates a clearly labelled sample fixture, exercises the native editor and approval controls, renders the app to `preview.png` in the isolated data directory, and exits. It does not call an LLM. Actual writing quality and inference speed depend on your model and hardware.

API references: [Ollama generate](https://docs.ollama.com/api/generate), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

MIT licensed. See [LICENSE](LICENSE).
