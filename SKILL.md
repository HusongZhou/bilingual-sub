---
name: bilingual-sub
description: 用户给出 YouTube 视频链接，要求做中英双语字幕、给视频加中文字幕、做双语学习视频、翻译视频字幕并嵌入视频时使用。默认输出「原视频 + 可开关的中英双语软字幕」；只有用户明确说要「烧录 / 烧进画面 / 硬字幕 / burn」时才把字幕烧进画面。只要文字稿或总结时用 youtube-transcripts，不用本 skill。
---

# YouTube 中英双语字幕

一条命令：下载视频、封面和英文字幕 → 翻译成中文 → 生成中英双语字幕并嵌入视频。

脚本必须用**真实路径**调用（不要经由 skills 目录联接调用，脚本根据自身位置计算默认输出目录）：

```bash
"/e/Asset Library/youtube/tools/bilingual-sub/bilingual_sub.sh" "<URL>" --engine deepseek
```

在 Bash 工具（Git Bash）里运行，不要用 PowerShell。下载加翻译通常要几分钟，用 `run_in_background` 跑，完成后再汇报。

## 默认行为与烧录

- **默认（不加 `--burn`）**：软字幕。输出 `<标题>_bilingual.mp4`，字幕作为轨道嵌入，播放器里可开关；不重新编码，很快。
- **仅当用户明确要求烧录**（「烧录」「烧进画面」「硬字幕」「burn」「字幕要一直显示」等）才加 `--burn`，输出 `<标题>_burned.mp4`。烧录要重新编码整段视频，有 NVIDIA 显卡时用 GPU，否则 CPU 较慢；不确定用户是否要烧录时，按默认软字幕做，不要擅自烧录。
- 同一视频已做过软字幕、之后再要烧录：直接加 `--burn` 重跑，已有的 `.bilingual.srt` 会被复用，不会重复翻译；软字幕版保留不被覆盖。

## 翻译引擎

- 用户没指定时用 `--engine deepseek`（本机已配置 `DEEPSEEK_API_KEY`）。若报缺 key，改用 `--engine google`（免 key）并告知用户。
- 用户指定时照做：`google` | `deepl` | `microsoft` | `yandex` | `claude` | `deepseek` | `openai`；`--model` 可换模型。
- 用户提到视频背景（节目名、人物、主题）时，用 `--context "..."` 传给大模型，帮助翻准人名和梗。可从视频标题推断一句简短背景。
- key 读取顺序：`--api-key` > 环境变量（含 Windows 用户级变量）> 脚本目录的 `.env`。不要把 key 写进命令行输出或聊天。

## 其他参数

| 参数 | 说明 |
|---|---|
| `--out-dir DIR` | 输出根目录；默认 `E:\Asset Library\youtube` |
| `--context "..."` | 视频背景 |
| `--burn` | 烧录（仅用户明确要求时） |
| `--post` | 顺带生成 B 站投稿简报（交给 bilibili-post） |

## 输出

```
<out-dir>/<视频标题>/
├── <标题>.mp4                  原视频
├── <标题>.jpg                  封面
├── <标题>.info.json            原视频信息（频道、日期、播放量、简介），B 站投稿包会用
├── <标题>.en.srt               英文字幕
├── <标题>.en.bilingual.srt     双语字幕（可外挂）
├── <标题>_bilingual.mp4        软字幕版（默认）
└── <标题>_burned.mp4           烧录版（仅 --burn）
```

## 接着发 B 站

用户如果同时要 B 站投稿信息（标题、标签、简介），两种接法：

- **一条命令跑完**：加 `--post`，视频做好后自动生成 `bili/brief.md`（元数据、章节、候选钩子段）和 `bili/transcript.txt`，最后打印 `brief: <路径>`。然后按 `bilibili-post` 的 SKILL.md 接着写投稿包。
- **分两次**：先跑本脚本，再把 `<视频标题>` 文件夹交给 `bilibili-post` skill。

`--post` 只准备数据，不写文案；标题、简介、标签是 bilibili-post 的活。

做字幕算「个人学习」，发 B 站算「转载」，两件事别混：发之前确认转载声明写全、没有编造授权。

## 汇报

- 以脚本最后一行 `Done: <路径>` 为准，给出输出文件夹和成品视频路径；没看到 `Done:` 不算完成。
- 加了 `--post` 时，再以 `brief:` 那行为简报路径。
- 可读几行 `.bilingual.srt` 抽查翻译质量（英文在上、中文在下）。
- 常见失败：视频没有英文字幕（脚本会打印 yt-dlp 输出）、缺 ffmpeg（`winget install ffmpeg`）、API key 无效。如实转述错误，不要声称成功。
- 软字幕版在 Windows 自带播放器里可能看不到字幕或需 AV1 扩展，推荐 VLC / PotPlayer。
- 仅供个人学习，遵守 YouTube 条款和版权。
