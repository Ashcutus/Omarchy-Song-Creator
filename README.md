# Versework — Omarchy Song Creator

A native GTK 4 app for writing **songs** with a local Ollama model. Develop a song on its own, collect ideas around a theme, and organise an album or EP when you want to. Copy the finished lyrics and settings into Suno yourself; no Suno API is needed.

## Install on Omarchy

```bash
git clone https://github.com/Ashcutus/Omarchy-Versework.git &&
cd Omarchy-Versework &&
./install.sh &&
./setup-ollama.sh
```

The installer asks where to place the music-note icon: **Left**, **Middle**, **Right**, or **No icon**. Click the icon to open Versework. It follows the bar's native theme. This requires the Omarchy shell and installation from a terminal in your running desktop session.

To move the icon later, rerun the installer and choose another position. This moves the existing icon without duplicating it. **Keep current layout** leaves its placement unchanged; **No icon** disables a previously installed icon. Other bar widgets are preserved.

For an installation without prompts:

```bash
./install.sh --bar-position middle
```

Use `left`, `middle`, `right`, `none`, or `keep`. Without a terminal or an explicit option, the installer keeps the existing bar layout.

Search for **Versework — Song Creator** in the app launcher. The installer copies the app to `~/.local/share/versework/app` and adds a user-level desktop entry. Run `./install.sh` again after updating the repository, then close and reopen Versework. Your saved work is kept separately.

GTK 4 and Python GObject are normally already installed on Omarchy. If needed:

```bash
omarchy pkg add python-gobject gtk4
```

`setup-ollama.sh` installs `ollama` and `ollama-vulkan` through Omarchy, starts a loopback-only Ollama server, and downloads **qwen3:8b** (approximately 5 GB). Package installation may ask for your system password. Vulkan acceleration depends on the GPU driver and Ollama build.

To use a different local model, pass its name to the setup script. Then choose **Settings → Local writing → Check connection**, select it, and **Apply**. If Ollama is stopped after restarting your computer, use **Start Ollama** in the same section. No cloud model or API key is required.

To run directly from the repository:

```bash
./launch.sh
```

## Update Versework

Open **Settings → App updates → Check for updates**. If one is available, choose **Install update**, then **Restart Versework**. Updates come from this repository’s main branch and require internet access and Git. No terminal or administrator password is needed.

The updater stages and validates the new app before replacing the installed files. Your songs, settings, Ollama installation, and bar placement stay intact. If you run Versework directly from a source checkout, use the installed app for this feature.

To get this button in an older installation, merge the updater change, close Versework, and run this once from your repository folder:

```bash
git pull && ./install.sh --bar-position keep
```

## Songs first

Use **Open Suno** in the top bar to open Suno’s creation page in your default browser. Log in there if needed; Versework does not handle your Suno credentials or send song text automatically.

- **New song** starts with one song by default. Enter its working title, style, optional theme, lyric language, target duration range and rewrite limit. You can request several song ideas at once.
- The **Songs** library shows all your songs, including unfinished drafts, and searches titles, styles and themes.
- Each song has **Lyrics**, **Sound** and **Review** tabs. All eight fields are editable and individually copyable: title, lyrics, style prompt, exclusions, vocal gender, weirdness %, style influence %, and variety (`off`, `normal`, `high`, `extra`, `max`).
- **Style prompt** and **Exclusions** each allow up to **1,000 characters**, including spaces and punctuation. Their editors show a live count and reject typing or pasting beyond the limit. This also applies to the initial style brief and AI output. Existing longer saved text is preserved for shortening; it is never silently truncated.
- **Refresh lyrics** on the Lyrics tab offers Light polish, Stronger chorus, Fresh lyrics, and Update delivery cues. Choosing one appends editable instructions to Review; it does not start generation. Click **Rewrite song** when ready. Existing locks and rewrite limits apply.
- Write a draft, give feedback, lock fields you want preserved exactly, and approve it when ready. Version history preserves earlier drafts and manual edits.
- Generate audio manually in Suno, then bring your listening notes back into **Review**. Target duration guides the writing; Suno determines the audio length.

## Control production and delivery

In **New song → Production direction**, choose production density, dynamics, vocal delivery and performance feel, then add specific arrangement notes. New songs default to **Restrained** production; other controls follow your style until you choose otherwise. Existing songs keep their original direction until you change it.

**Performance feel** offers **Natural and understated** (subtle timing variation and unforced phrasing), **Live-room performance** (responsive ensemble timing and minimal editing), or **Tight and polished**. Follow style leaves this choice open. These provide concrete delivery cues and exclusions; they cannot guarantee that Suno sounds human or remove every synthetic artefact.

Use the **Production** button on any song to adjust its next draft or rewrite. For a sparse result, try **Stripped back**, **Steady and contained**, and **Intimate solo**, with notes such as “Fingerpicked guitar and one dry lead voice; leave silence between phrases.”

For both new drafts and rewrites (including collection updates), Versework supplies explicit production phrases for the style prompt, bracketed performance cues for the lyrics, and relevant exclusions. It checks that the model includes them in unlocked fields and retries once if they are missing. A second omission leaves your draft and rewrite allowance unchanged. Freeform arrangement notes are also sent as creative direction; their meaning is not automatically verified. Saving direction does not change existing lyrics: generate a draft or use Review to request a rewrite. Locked fields and rewrite limits still apply. Suno may interpret the instructions differently; this is creative direction, not direct control of its audio engine.

## Optional collections, albums and EPs

Use **New collection** to name a group, give it a theme and choose songs. A collection may be labelled **Collection**, **Album** or **EP**; change that at any time under **Manage collection**. The up/down controls determine running order. A song can belong to more than one collection.

Use **Organise song** from the editor to change membership. Removing a song from a collection leaves the song and every saved version in the library. Collection themes add context when writing a song opened from that collection; they do not overwrite individual song briefs or lyric languages. Songs opened from the unfiltered library use their own brief.

**Review songs** lets you apply feedback to selected eligible songs in a collection. Approved songs and songs at their rewrite limit are excluded. **Export** saves readable song text plus a JSON snapshot of the selected songs, creative briefs and version histories.

Earlier multi-song projects are automatically represented as collections on first launch of this version. The original song records, approvals, locks and rewrite histories remain unchanged. This migration runs only once.

## Appearance and interface language

**Settings** is always dismissible with **Close**, the window close control, or **Escape**. Closing discards changes that have not been applied. **Apply** saves preferences and closes Settings, including when nothing has changed. If validation fails, Settings stays open so you can correct the error. Local writing controls are in a collapsible section and are not required for changing appearance or closing the window.

### Theme and colours

The default is **Follow Omarchy theme**. Versework reads the active Omarchy palette at `~/.local/state/omarchy/current/theme/colors.toml` (with the older `~/.config/omarchy/current/theme` location as a fallback) and follows changes automatically. The interface uses Omarchy’s configured monospace font, compact square controls, thin accent borders, and subdued panels. It leaves desktop settings and global configuration untouched. If no Omarchy palette is available, GTK supplies the native colours; the app does not force dark mode.

Choose **Custom colours** to change Versework's background, surfaces, text and accent using colour pickers or six-digit hex values. **Restore theme colours**, then **Apply**, returns to automatic theme following. These preferences affect Versework only.

### Interface language

The default is **System language**, resolved from the user's locale environment (`LC_ALL`, `LC_MESSAGES`, `LANG` and GNU `LANGUAGE` preferences). Available translations: **English, German, Spanish and French**. Unsupported system languages fall back to English. The setting remains “system” rather than storing a detected language, so future launches follow locale changes.

You may explicitly select an interface language. This changes menus, buttons and built-in interface text, **not song content, creative briefs or lyric language**. Generated content and detailed external service errors remain in their original language.

## Revision rules

- Initial drafts do not consume a rewrite.
- Only a successfully validated, saved AI revision increments the song's counter. Unchanged output, even if its notes claim changes, is rejected without using a rewrite.
- Manual edits and restoring an earlier version do not use an AI rewrite or reset the counter.
- Approved songs are protected until reopened. Reopening does not reset the rewrite limit.
- Reaching the limit marks a song **Limit reached · review needed**; it never approves a song automatically.
- Locked fields are enforced by the app.
- Initial drafts are checked for repeated substantial lines from other songs in the writing context. Two or more repeated lines trigger one automatic retry; a second duplicate result is rejected. This exact-line check is not a guarantee of originality.
- Completed drafts are saved as generation progresses. A later failure does not discard earlier songs.
- **Stop writing** cancels at the next streamed response; first-time model loading may delay cancellation. Closing preserves completed, saved drafts.

## Storage and privacy

Songs, collections, settings and version history are stored in `~/.local/share/versework/data/projects.sqlite3` using SQLite transactions. Back up the whole data folder while the app is closed to preserve full app state. Exports are readable text and JSON snapshots; the app does not yet import those JSON exports.

For AI writing, the app only connects to `http://127.0.0.1:11434`, bypasses HTTP proxies, and excludes models advertised as cloud or remote. Its Ollama startup sets `OLLAMA_NO_CLOUD=1`. Downloading a model needs internet access; writing uses the installed local model. Ollama may stay running after the app closes and logs to `~/.local/share/versework/data/ollama.log` when started by Versework.

## Development and validation

Python 3.11+, GTK 4.10+ and PyGObject are the app dependencies. There are no pip dependencies. Ollama is accessed through its documented streaming `/api/generate` API with a JSON schema and local validation.

```bash
python -m unittest discover -v
python -m py_compile app.py core.py appearance.py i18n.py
bash -n install.sh launch.sh setup-ollama.sh
```

The tests cover revision and approval rules, duplicate/unchanged output, persistence, collection migration and membership, generation context, palette validation and locale selection. Run the native UI smoke test with an isolated data directory:

```bash
VERSEWORK_DATA=/tmp/versework-smoke ./launch.sh --smoke
```

It verifies native editor construction, approval/reopening, settings dismissal without applying, settings reopening, language/colour application and reset, and preservation of song content. It renders `preview.png`, `settings.png` and `library.png` into that isolated directory and exits. It uses labelled fixtures and does not call an LLM.

API references: [Ollama generate](https://docs.ollama.com/api/generate), [structured outputs](https://docs.ollama.com/capabilities/structured-outputs).

MIT licensed. See [LICENSE](LICENSE).
