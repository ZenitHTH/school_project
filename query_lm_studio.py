import argparse
import json
import sys
import time
import urllib.error
import urllib.request

LM_STUDIO_HOST = "http://100.115.25.30:1234"


def switch_context(context_length: int = 131072, model: str = "google/gemma-4-12b-qat") -> bool:
    """Unload existing model instances and reload with target context length."""
    print(f"[*] Switching {model} to {context_length} context length...")
    # 1. Inspect loaded models
    try:
        req = urllib.request.Request(f"{LM_STUDIO_HOST}/api/v0/models")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for m in data.get("data", []):
                if m.get("state") == "loaded":
                    inst_id = m.get("id")
                    print(f"[*] Unloading existing instance: {inst_id}")
                    unload_payload = json.dumps({"instance_id": inst_id}).encode("utf-8")
                    unload_req = urllib.request.Request(
                        f"{LM_STUDIO_HOST}/api/v1/models/unload",
                        data=unload_payload,
                        headers={"Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(unload_req, timeout=10):
                        pass
    except Exception as e:
        print(f"[!] Warning checking/unloading instances: {e}")

    eval_batch = 512 if "qwen" in model.lower() else 1024
    load_payload = json.dumps({
        "model": model,
        "context_length": context_length,
        "eval_batch_size": eval_batch,
        "flash_attention": True,
        "offload_kv_cache_to_gpu": True
    }).encode("utf-8")

    try:
        load_req = urllib.request.Request(
            f"{LM_STUDIO_HOST}/api/v1/models/load",
            data=load_payload,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(load_req, timeout=60) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"[+] Loaded {res.get('instance_id')} in {res.get('load_time_seconds')}s with status: {res.get('status')}")
            return True
    except Exception as e:
        print(f"[!] Failed to load model with context {context_length}: {e}")
        return False


def query_stream(
    prompt: str,
    system_prompt: str = None,
    max_tokens: int = 16000,
    model: str = "google/gemma-4-12b-qat",
    think_longer: bool = False,
    show_thinking: bool = False,
):
    messages = []
    
    # Directive for longer thinking / deep reasoning
    if think_longer:
        deep_think_directive = (
            "You are an expert software engineer and systems architect. "
            "Think exhaustively, deeply, and thoroughly step-by-step. "
            "Analyze every requirement, investigate edge cases, verify invariants, "
            "trace state transitions, and rigorously double-check your code logic "
            "in your thinking process before presenting the final solution."
        )
        if system_prompt:
            combined_system = f"{deep_think_directive}\n\n{system_prompt}"
        else:
            combined_system = deep_think_directive
        messages.append({"role": "system", "content": combined_system})
    elif system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({"role": "user", "content": prompt})

    temperature = 0.6 if think_longer else 0.2

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True
    }

    req = urllib.request.Request(
        f"{LM_STUDIO_HOST}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    reasoning = []
    content = []
    start = time.time()

    if show_thinking:
        print("\n--- Thinking Process ---")

    with urllib.request.urlopen(req, timeout=600) as resp:
        for line in resp:
            line = line.decode("utf-8").strip()
            if not line.startswith("data: ") or line.endswith("[DONE]"):
                continue
            data = json.loads(line[6:])
            delta = data["choices"][0].get("delta", {})

            if "reasoning_content" in delta and delta["reasoning_content"]:
                rc = delta["reasoning_content"]
                reasoning.append(rc)
                if show_thinking:
                    sys.stdout.write(rc)
                    sys.stdout.flush()

            if "content" in delta and delta["content"]:
                if show_thinking and len(content) == 0:
                    print("\n\n--- Final Response ---")
                c = delta["content"]
                content.append(c)
                sys.stdout.write(c)
                sys.stdout.flush()

    duration = time.time() - start
    print(f"\n\n[Done in {duration:.1f}s, reasoning: {len(reasoning)} tokens, content: {len(content)} tokens]")
    return "".join(content)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query local LM Studio instance with context and thinking controls")
    parser.add_argument("prompt", nargs="?", default="Hello", help="User prompt to send")
    parser.add_argument("--system", default=None, help="System prompt")
    parser.add_argument("--context", type=int, default=None, help="Context length to switch to (e.g. 131072 for 128k, 32768 for 32k)")
    parser.add_argument("--128k", action="store_true", dest="set_128k", help="Convenience flag for 131072 (128k) context")
    parser.add_argument("--think-longer", action="store_true", help="Command model to think deeply and step-by-step")
    parser.add_argument("--show-thinking", action="store_true", help="Stream reasoning output in real-time")
    parser.add_argument("--max-tokens", type=int, default=16000, help="Max tokens budget for completion + reasoning")
    parser.add_argument("--model", default="google/gemma-4-12b-qat", help="Model ID")

    args = parser.parse_args()

    if args.set_128k:
        switch_context(context_length=131072, model=args.model)
    elif args.context:
        switch_context(context_length=args.context, model=args.model)

    query_stream(
        prompt=args.prompt,
        system_prompt=args.system,
        max_tokens=args.max_tokens,
        model=args.model,
        think_longer=args.think_longer,
        show_thinking=args.show_thinking,
    )
