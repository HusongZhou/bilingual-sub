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

- **一条命令跑完**：下载 → 翻译 → 嵌入字幕
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
├── <标题>.en.srt               英文字幕
├── <标题>.en.bilingual.srt     双语字幕（可外挂）
└── <标题>_bilingual.mp4        嵌入双语字幕的视频
```

### 常用参数

| 参数 | 说明 |
|---|---|
| `--engine` | `google`（默认）\| `deepl` \| `microsoft` \| `yandex` \| `claude` \| `deepseek` \| `openai` |
| `--model` | 模型名。deepseek 默认 `deepseek-flash`，claude 默认 `claude-opus-5-5` |
| `--context "..."` | 视频背景，帮助大模型翻准人名和梗 |
| `--out-dir DIR` | 输出根目录 |
| `--burn` | 把字幕烧进画面（会重新编码，较慢） |
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
```

### 只翻译一个 srt 文件

```bash
python translate_srt.py input.en.srt --engine deepseek
```

## 注意

- 视频需要有英文字幕（人工或自动生成都可以）
- YouTube 高清视频常是 AV1 编码，Windows 自带播放器可能需要装 AV1 扩展；VLC、PotPlayer 可直接播放
- 请仅用于个人学习，遵守 YouTube 服务条款和视频版权
