"""Translate an English .srt into a stacked English/Chinese bilingual .srt.

Usage:
    python translate_srt.py input.srt [-o output.srt] [--engine ENGINE] [options]

Machine-translation engines (one line at a time):
    google      no key needed (default)
    deepl       --api-key
    microsoft   --api-key, optional --region
    yandex      --api-key

LLM engines (translate in batches, so they see the surrounding dialogue):
    claude      Anthropic API. Key from --api-key or ANTHROPIC_API_KEY.
                --model defaults to claude-opus-5-5.
    deepseek    DeepSeek. Key from --api-key or DEEPSEEK_API_KEY. --model defaults to deepseek-flash.
    openai      Any OpenAI-compatible endpoint: DeepSeek, Qwen, Kimi, OpenAI, local Ollama...
                --base-url, --model, key from --api-key or OPENAI_API_KEY.
                e.g. DeepSeek: --base-url https://api.deepseek.com --model deepseek-chat

LLM options:
    --context "..."   what the video is about, e.g. "Ted Lasso S2 character analysis"
    --batch-size N    subtitle lines per request (default 40)
"""
import argparse
import os
import re
import sys
import pysrt

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


def machine_translator(engine, api_key, region):
    from deep_translator import (
        GoogleTranslator,
        DeeplTranslator,
        MicrosoftTranslator,
        YandexTranslator,
    )

    if engine != "google" and not api_key:
        sys.exit(f"{engine} engine needs --api-key")
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

    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

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

    client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"), base_url=base_url)

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

    if args.engine == "claude":
        complete = claude_complete(args.api_key, args.model or "claude-opus-5-5")
        translate = llm_translator(complete, args.context, args.batch_size)
    elif args.engine == "deepseek":
        key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            sys.exit("deepseek engine needs DEEPSEEK_API_KEY (or --api-key)")
        complete = openai_complete(
            key, args.model or "deepseek-flash", args.base_url or "https://api.deepseek.com"
        )
        translate = llm_translator(complete, args.context, args.batch_size)
    elif args.engine == "openai":
        if not args.model:
            sys.exit("openai engine needs --model (e.g. deepseek-chat)")
        complete = openai_complete(args.api_key, args.model, args.base_url)
        translate = llm_translator(complete, args.context, args.batch_size)
    else:
        translate = machine_translator(args.engine, args.api_key, args.region)

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
