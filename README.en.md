# bilingual-sub

[中文](README.md) | **English**

Give it a YouTube URL: it downloads the video and its English subtitles, translates them into Chinese, and embeds **stacked English/Chinese subtitles** into the video. Built for learning English from videos.

## What it looks like

Each subtitle shows the English line with the Chinese translation beneath it:

```
i worked my ass off
我拼了老命
```

## Features

- **One command, end to end**: download → translate → embed subtitles
- **LLM translation**: DeepSeek, Claude, or any OpenAI-compatible model (Qwen, Kimi, local Ollama, ...). Lines are sent 40 at a time so the model sees the surrounding dialogue and handles slang, idioms and jokes naturally. Use `--context` to tell the model what the video is about
- **Machine translation too**: Google (no key), DeepL, Microsoft, Yandex
- **Handles auto-generated captions**: YouTube's auto captions overlap in time, which would stack four lines on screen once bilingual; the script trims the overlaps. Lines the model skips are re-translated automatically
- **Two ways to embed**: a soft subtitle track by default (toggle it in your player), or `--burn` to render it permanently into the frame

## Requirements

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/) (Windows: `winget install ffmpeg`)
- Python 3.9+
- bash (Git Bash on Windows)

```bash
pip install -r requirements.txt
```

## API keys

```bash
cp .env.example .env
```

Then fill in the keys for the engines you use (only those). `.env` is git-ignored and never committed.

Lookup order: `--api-key` on the command line > environment variables > `.env`.

## Usage

```bash
./bilingual_sub.sh "https://www.youtube.com/watch?v=xxxx" --engine deepseek
```

Output goes to a folder named after the video title, two levels above the script (change it with `--out-dir`):

```
<out-dir>/<video title>/
├── <title>.mp4                  original video
├── <title>.en.srt               English subtitles
├── <title>.en.bilingual.srt     bilingual subtitles (usable as an external sub file)
└── <title>_bilingual.mp4        video with bilingual subtitles embedded
```

### Options

| Option | Description |
|---|---|
| `--engine` | `google` (default) \| `deepl` \| `microsoft` \| `yandex` \| `claude` \| `deepseek` \| `openai` |
| `--model` | Model name. Defaults: `deepseek-flash` for deepseek, `claude-opus-5-5` for claude |
| `--context "..."` | What the video is about, so the LLM gets names and references right |
| `--out-dir DIR` | Output root folder |
| `--burn` | Burn subtitles into the frame (re-encodes the video, slower) |
| `--api-key KEY` | Use this key for this run, overriding `.env` |

### Examples

```bash
# DeepSeek, with some context about the video
./bilingual_sub.sh "URL" --engine deepseek --context "Ted Lasso S2 character analysis"

# Claude
./bilingual_sub.sh "URL" --engine claude

# Another OpenAI-compatible API (set OPENAI_BASE_URL / OPENAI_MODEL in .env)
./bilingual_sub.sh "URL" --engine openai

# Burn subtitles into the frame
./bilingual_sub.sh "URL" --engine deepseek --burn
```

### Translate a single .srt file

```bash
python translate_srt.py input.en.srt --engine deepseek
```

## Notes

- The video needs English subtitles (manual or auto-generated)
- HD YouTube videos are often AV1-encoded; the built-in Windows player may need the AV1 extension, while VLC and PotPlayer play them directly
- For personal study only. Respect YouTube's Terms of Service and the video's copyright
