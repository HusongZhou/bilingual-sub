# bilingual-sub

**中文** | [English](README.en.md)

输入一个 YouTube 链接，自动下载视频和英文字幕，翻译成中文，生成**中英双语字幕**并嵌入视频。适合看英文视频学英语。

## 效果

每条字幕上面英文、下面中文：

```
i worked my ass off
我拼了老命
```

## 特点

- **一条命令跑完**：下载视频和封面 → 翻译 → 嵌入字幕
- **可选大模型翻译**：DeepSeek、Claude，或任何兼容 OpenAI 接口的模型（通义、Kimi、本地 Ollama 等）。每 40 句一批翻译，模型能看到上下文，口语、俚语、梗翻得更自然；可用 `--context` 告诉模型视频在讲什么
- **也支持机器翻译**：Google（免 key）、DeepL、微软、Yandex
- **处理自动字幕**：YouTube 自动生成的字幕时间轴互相重叠，双语后会叠出四行，脚本会自动裁开；漏翻的行会自动补翻
- **两种嵌入方式**：默认软字幕（播放器里可开关），加 `--burn` 永久烧进画面

## 依赖

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [ffmpeg](https://ffmpeg.org/)（Windows：`winget install ffmpeg`）
- Python 3.9+
- bash（Windows 上用 Git Bash）

```bash
pip install -r requirements.txt
```

## 配置 API key

```bash
cp .env.example .env
```

然后在 `.env` 里填上你要用的引擎的 key（只填用得到的即可）。`.env` 已被 git 忽略，不会提交。

读取顺序：命令行 `--api-key` > 系统环境变量 > `.env`。

## 用法

```bash
./bilingual_sub.sh "https://www.youtube.com/watch?v=xxxx" --engine deepseek
```

输出在脚本上两级目录下，以视频标题命名的文件夹里（可用 `--out-dir` 改）：

```
<out-dir>/<视频标题>/
├── <标题>.mp4                  原视频
├── <标题>.jpg                  视频封面
├── <标题>.info.json            原视频信息（频道、发布日期、播放量、简介、标签）
├── <标题>.en.srt               英文字幕
├── <标题>.en.bilingual.srt     双语字幕（可外挂）
├── <标题>_bilingual.mp4        软字幕版（默认）
└── <标题>_burned.mp4           字幕烧进画面的版本（加 --burn 时生成）
```

### 常用参数

| 参数 | 说明 |
|---|---|
| `--engine` | `google`（默认）\| `deepl` \| `microsoft` \| `yandex` \| `claude` \| `deepseek` \| `openai` |
| `--model` | 模型名。deepseek 默认 `deepseek-flash`，claude 默认 `claude-opus-5-5` |
| `--context "..."` | 视频背景，帮助大模型翻准人名和梗 |
| `--out-dir DIR` | 输出根目录 |
| `--burn` | 把字幕烧进画面，另存为 `_burned.mp4`。有 NVIDIA 显卡时自动用显卡编码，否则用 CPU（较慢） |
| `--post` | 顺带生成 B 站投稿简报，交给 [bilibili-post](../bilibili-post) 写标题、简介、标签 |
| `--api-key KEY` | 临时指定 key，覆盖 `.env` |

### 例子

```bash
# DeepSeek，附上视频背景
./bilingual_sub.sh "URL" --engine deepseek --context "Ted Lasso S2 character analysis"

# Claude
./bilingual_sub.sh "URL" --engine claude

# 其他 OpenAI 兼容接口（在 .env 里配好 OPENAI_BASE_URL / OPENAI_MODEL）
./bilingual_sub.sh "URL" --engine openai

# 字幕烧进画面
./bilingual_sub.sh "URL" --engine deepseek --burn

# 下完顺手备好 B 站投稿简报（标题、简介、标签接着让 bilibili-post 写）
./bilingual_sub.sh "URL" --engine deepseek --post
```

### 只翻译一个 srt 文件

```bash
python translate_srt.py input.en.srt --engine deepseek
```

## 注意

- 视频需要有英文字幕（人工或自动生成都可以）
- 同一个视频重跑时（比如先生成软字幕版、再加 `--burn`），已有的 `.bilingual.srt` 会直接复用，不会重复翻译；想重新翻译就先删掉它
- YouTube 高清视频常是 AV1 编码，Windows 自带播放器可能需要装 AV1 扩展；VLC、PotPlayer 可直接播放
- 请仅用于个人学习，遵守 YouTube 服务条款和视频版权

## License

[MIT](LICENSE)。本许可只针对本仓库的代码，不涉及你用它下载的视频内容。
