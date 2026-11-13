"""Translate an English .srt into a stacked English/Chinese bilingual .srt.

Usage:
    python translate_srt.py input.srt [-o output.srt] [--engine ENGINE] [options]

API keys come from --api-key, else the environment, else a .env file next to this
script (see .env.example).

Machine-translation engines (one line at a time):
    google      no key needed (default)
    deepl       DEEPL_API_KEY
    microsoft   MICROSOFT_TRANSLATOR_KEY, MICROSOFT_TRANSLATOR_REGION (or --region)
    yandex      YANDEX_API_KEY

LLM engines (translate in batches, so they see the surrounding dialogue):
    claude      ANTHROPIC_API_KEY. --model defaults to claude-opus-5-5.
    deepseek    DEEPSEEK_API_KEY. --model defaults to deepseek-flash.
    openai      Any OpenAI-compatible endpoint: Qwen, Kimi, OpenAI, local Ollama...
                OPENAI_API_KEY, OPENAI_BASE_URL (or --base-url), OPENAI_MODEL (or --model).

LLM options:
    --context "..."   what the video is about, e.g. "Ted Lasso S2 character analysis"
    --batch-size N    subtitle lines per request (default 40)
"""
import argparse
import os
import re
import sys
import pysrt

KEY_VARS = {
    "claude": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepl": "DEEPL_API_KEY",
    "microsoft": "MICROSOFT_TRANSLATOR_KEY",
    "yandex": "YANDEX_API_KEY",
}

SYSTEM_PROMPT = (
    "You translate English video subtitles into natural, colloquial Simplified Chinese "
    "for a Chinese viewer who is learning English. Keep names in English. "
    "Keep the meaning of jokes, idioms and slang rather than translating word by word. "
    "Lines may be auto-generated captions with no punctuation, and one sentence may be split "
    "across several lines: use the surrounding lines to understand it, but translate each line "
    "on its own so it stays aligned with the English on screen. "
    "You receive numbered lines in the form `N|text`. Reply with exactly the same numbers, "
    "one per line, in the form `N|translation`, and nothing else."
)


def load_dotenv(path):
    """Set KEY=VALUE pairs from a .env file; variables already in the environment win."""
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.removeprefix("export ").split("=", 1)
            key, value = key.strip(), value.strip().strip("'\"")
            if value and key not in os.environ:
                os.environ[key] = value


def machine_translator(engine, api_key, region):
    from deep_translator import (
        GoogleTranslator,
        DeeplTranslator,
        MicrosoftTranslator,
        YandexTranslator,
    )

    if engine == "google":
        t = GoogleTranslator(source="en", target="zh-CN")
    elif engine == "deepl":
        t = DeeplTranslator(api_key=api_key, source="en", target="zh", use_free_api=True)
    elif engine == "microsoft":
        t = MicrosoftTranslator(api_key=api_key, region=region, source="en", target="zh-Hans")
    elif engine == "yandex":
        t = YandexTranslator(api_key=api_key, source="en", target="zh")
    else:
        sys.exit(f"unknown engine: {engine}")
    return lambda lines: [t.translate(line) for line in lines]


def claude_complete(api_key, model):
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)

    def complete(system, user):
        response = client.beta.messages.create(
            model=model,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "low"},
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Claude declined this batch")
        return "".join(b.text for b in response.content if b.type == "text")

    return complete


def openai_complete(api_key, model, base_url):
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(system, user):
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content

    return complete


def parse_numbered(text):
    result = {}
    for line in text.splitlines():
        m = re.match(r"\s*(\d+)\s*\|\s*(.*)", line)
        if m:
            result[int(m.group(1))] = m.group(2).strip()
    return result


def llm_translator(complete, context, batch_size):
    system = SYSTEM_PROMPT + (f"\n\nAbout this video: {context}" if context else "")

    def ask(lines):
        user = "\n".join(f"{i + 1}|{line}" for i, line in enumerate(lines))
        got = parse_numbered(complete(system, user))
        return [got.get(i + 1) for i in range(len(lines))]

    def translate(lines):
        out = []
        for start in range(0, len(lines), batch_size):
            batch = lines[start:start + batch_size]
            zh = ask(batch)
            missing = [i for i, z in enumerate(zh) if not z]
            if missing:
                retry = ask([batch[i] for i in missing])
                for i, z in zip(missing, retry):
                    zh[i] = z or ""
            out.extend(zh)
            print(f"  {min(start + batch_size, len(lines))}/{len(lines)} lines")
        return out

    return translate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("-o", "--output")
    parser.add_argument("--engine", default="google")
    parser.add_argument("--api-key")
    parser.add_argument("--region")
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--context")
    parser.add_argument("--batch-size", type=int, default=40)
    args = parser.parse_args()

    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
    if args.engine != "google" and args.engine not in KEY_VARS:
        sys.exit(f"unknown engine: {args.engine}")
    key = None
    if args.engine in KEY_VARS:
        key = args.api_key or os.environ.get(KEY_VARS[args.engine])
        if not key:
            sys.exit(f"{args.engine} engine needs {KEY_VARS[args.engine]} (in .env or the environment) or --api-key")

    if args.engine == "claude":
        complete = claude_complete(key, args.model or "claude-opus-5-5")
        translate = llm_translator(complete, args.context, args.batch_size)
    elif args.engine == "deepseek":
        complete = openai_complete(
            key, args.model or "deepseek-flash", args.base_url or "https://api.deepseek.com"
        )
        translate = llm_translator(complete, args.context, args.batch_size)
    elif args.engine == "openai":
        model = args.model or os.environ.get("OPENAI_MODEL")
        if not model:
            sys.exit("openai engine needs OPENAI_MODEL (in .env) or --model")
        complete = openai_complete(key, model, args.base_url or os.environ.get("OPENAI_BASE_URL"))
        translate = llm_translator(complete, args.context, args.batch_size)
    else:
        region = args.region or os.environ.get("MICROSOFT_TRANSLATOR_REGION")
        translate = machine_translator(args.engine, key, region)

    out_path = args.output or args.input[: -len(".srt")] + ".bilingual.srt"
    subs = pysrt.open(args.input, encoding="utf-8")
    en_lines = [sub.text.replace("\n", " ") for sub in subs]
    zh_lines = translate(en_lines)

    for sub, en, zh in zip(subs, en_lines, zh_lines):
        sub.text = f"{en}\n{zh}"
    # Auto-captions overlap each cue with the next, which stacks 4 lines on screen once bilingual.
    for cur, nxt in zip(subs, subs[1:]):
        if cur.end > nxt.start:
            cur.end = nxt.start
    subs.save(out_path, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
