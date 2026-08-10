#!/usr/bin/env python3
"""
Unified LLM client for the Agentic Coder Fixer — High-End Edition.

Talks to up to 10 Ollama Cloud API keys / endpoints (any OpenAI-compatible
endpoint works) with:
  - Multi-provider ensemble: N models answer in PARALLEL, findings are merged
    by consensus (a finding survives if >= `ensemble.min_agreement` models
    agree, or a single high-confidence report). This gives autopilots
    "full knowledge" — one weak model can't gate a review.
  - Key failover (rotate API keys on 429/401) and model failover (5xx/timeout).
  - Retry with backoff, robust JSON extraction for structured outputs.
  - OLLAMA_HOST / AGENTIC_OLLAMA_HOST env override for local Ollama.

Key discovery order:
  1. config providers.ollama.endpoints[i].api_key_env  (explicit per endpoint)
  2. config providers.ollama.api_keys (inline array)
  3. env OLLAMA_API_KEY_1 .. OLLAMA_API_KEY_10
  4. env OLLAMA_API_KEYS (comma-separated)

Usage:
  from llm_client import LLMClient
  client = LLMClient()
  text = client.call("prompt", system="you are...")
  obj  = client.call_json("...", system="...")     # dict (ensemble-aware)
  lst  = client.call_json_list("...", system="...")# list (e.g. findings)
"""

import concurrent.futures
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import requests
except ImportError:
    sys.stderr.write("llm_client requires `requests`. Run: pip install requests\n")
    raise

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "agentic", "config.json")

_MAX_ENV_KEYS = 10
_ENV_KEY_NAMES = [f"OLLAMA_API_KEY_{i}" for i in range(1, _MAX_ENV_KEYS + 1)]


def load_config(path: Optional[str] = None) -> Dict[str, Any]:
    path = path or os.environ.get("AGENTIC_CONFIG") or DEFAULT_CONFIG
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class RateLimited(Exception):
    pass


class ProviderError(Exception):
    pass


class Endpoint:
    """One Ollama Cloud API endpoint (host) with its own keys and models."""

    def __init__(self, cfg: Dict[str, Any]):
        self.base_url = (os.environ.get("AGENTIC_OLLAMA_HOST")
                         or os.environ.get("OLLAMA_HOST")
                         or cfg.get("base_url", "https://ollama.com/v1")).rstrip("/")
        self.models = [m for m in cfg.get("models", []) if m]
        self.api_key_env = [e for e in cfg.get("api_key_env", []) if e]
        self.max_tokens = int(cfg.get("max_tokens", 4096))
        self.temperature = float(cfg.get("temperature", 0.1))
        self.timeout = int(cfg.get("timeout_seconds", 120))
        self.keys: List[str] = []

    def add_key(self, key: str) -> None:
        if key and key not in self.keys:
            self.keys.append(key)

    def combos(self) -> List[Tuple[str, str, Optional[str]]]:
        """(model, key) pairs; key may be None for local Ollama."""
        pairs = []
        for model in self.models:
            if self.keys:
                for key in self.keys:
                    pairs.append((model, key))
            else:
                pairs.append((model, None))
        return pairs


def _discover_endpoints(prov: Dict[str, Any]) -> List[Endpoint]:
    """Build endpoint list from config; attach up to 10 API keys each."""
    root_models = [m for m in prov.get("models", []) if m]
    ep_cfgs = prov.get("endpoints") or [prov]
    endpoints = []
    for c in ep_cfgs[: _MAX_ENV_KEYS]:
        merged = {**prov, **c}  # endpoint overrides root, inherits the rest
        ep = Endpoint(merged)
        if not ep.models:
            ep.models = list(root_models)
        endpoints.append(ep)

    # Inline keys from config.
    inline_keys = [k for k in prov.get("api_keys", []) if k]

    # Keys from env (global + per endpoint).
    env_keys = []
    for name in _ENV_KEY_NAMES:
        val = os.environ.get(name)
        if val and val not in env_keys:
            env_keys.append(val)
    for name in ["OLLAMA_API_KEY", "OLLAMA_API_KEYS", "NAS_LLM_API_KEY"]:
        val = os.environ.get(name)
        if val:
            for k in re.split(r"[\s,]+", val):
                if k and k not in env_keys:
                    env_keys.append(k)

    # Per-endpoint env override.
    for i, ep in enumerate(endpoints):
        for name in ep.api_key_env:
            val = os.environ.get(name)
            if val:
                ep.add_key(val)

    # Global pool: inline first, then env, spread round-robin across endpoints.
    pool = list(inline_keys) + env_keys
    for idx, key in enumerate(pool):
        endpoints[idx % len(endpoints)].add_key(key)

    return [ep for ep in endpoints if ep.models]


class LLMClient:
    """Ensemble-first, failover-second OpenAI-compatible chat client."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or load_config()
        prov = self.config.get("providers", {}).get("ollama", {})
        self.endpoints = _discover_endpoints(prov)
        self.ensemble_enabled = bool(self.config.get("ensemble", {}).get("enabled", True))
        ens = self.config.get("ensemble", {})
        self.top_k = int(ens.get("top_k", 3))
        self.min_agreement = int(ens.get("min_agreement", 2))
        self.high_confidence = float(ens.get("high_confidence", 0.85))
        self.max_tokens = int(prov.get("max_tokens", 4096))
        self.temperature = float(prov.get("temperature", 0.1))
        self.timeout = int(prov.get("timeout_seconds", 120))

    @property
    def has_keys(self) -> bool:
        return any(ep.keys for ep in self.endpoints)

    @property
    def model_count(self) -> int:
        return sum(len(ep.models) for ep in self.endpoints)

    # ── Public API ──────────────────────────────────────────────────────────

    def call(self, prompt: str, system: Optional[str] = None,
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None) -> Optional[str]:
        """Single LLM call with key+model failover across ALL endpoints.

        Returns the first successful text. If `ensemble.top_k > 1` and more
        than one model is available, this still returns the first success
        (failover semantics); use `call_json` for ensemble consensus.
        """
        messages = self._messages(system, prompt)
        combos = self._all_combos()
        last_error: Optional[Exception] = None

        for model, key, ep in combos:
            try:
                text = self._post(ep, messages, model, key, temperature, max_tokens)
                if text:
                    return text
            except RateLimited as e:
                last_error = e
                continue  # rotate key / endpoint
            except ProviderError as e:
                last_error = e
                continue  # rotate model / endpoint
            except Exception as e:
                last_error = e
                continue
        print(f"[llm] all providers failed: {last_error}", file=sys.stderr)
        return None

    def call_json(self, prompt: str, system: Optional[str] = None,
                  temperature: Optional[float] = None) -> Optional[Any]:
        """Ensemble call returning a parsed JSON value (dict or list).

        When ensemble is enabled and multiple models exist, several models run
        in parallel and the JSON responses are merged by consensus.
        """
        sys_prompt = (system or "") + (
            "\n\nRespond with a single valid JSON object and nothing else. "
            "Do not wrap it in markdown code fences."
        )
        if not self.ensemble_enabled:
            text = self.call(prompt, system=sys_prompt, temperature=temperature)
            return extract_json(text) if text else None

        results = self._ensemble_text(prompt, system=sys_prompt, temperature=temperature)
        parsed = [extract_json(t) for t in results if t]
        parsed = [p for p in parsed if p is not None]
        if not parsed:
            print("[llm] ensemble produced no parseable JSON", file=sys.stderr)
            return None
        if len(parsed) == 1:
            return parsed[0]
        return self._merge_json(parsed)

    def call_json_list(self, prompt: str, system: Optional[str] = None,
                       temperature: Optional[float] = None) -> List[Any]:
        """Like call_json but guaranteed to return a list (for findings/plans)."""
        out = self.call_json(prompt, system=system, temperature=temperature)
        if isinstance(out, list):
            return out
        if isinstance(out, dict) and isinstance(out.get("items"), list):
            return out["items"]
        if isinstance(out, dict) and isinstance(out.get("findings"), list):
            return out["findings"]
        return []

    def describe(self) -> str:
        lines = [f"LLM ensemble: {self.model_count} model(s), "
                 f"{sum(len(ep.keys) for ep in self.endpoints)} key(s), "
                 f"top_k={self.top_k}, min_agreement={self.min_agreement}"]
        for i, ep in enumerate(self.endpoints, 1):
            keys = len(ep.keys)
            lines.append(f"  [{i}] {ep.base_url} models={ep.models} keys={keys}")
        return "\n".join(lines)

    # ── Ensemble ────────────────────────────────────────────────────────────

    def _ensemble_text(self, prompt: str, system: Optional[str],
                       temperature: Optional[float]) -> List[str]:
        """Run top_k (model, endpoint) combos in parallel; return successful texts."""
        combos = self._all_combos()
        if len(combos) <= 1:
            text = self.call(prompt, system=system, temperature=temperature)
            return [text] if text else []

        # Prefer diversity: spread picks across endpoints/models.
        chosen: List[Tuple[str, str, Endpoint]] = []
        used_models, used_eps = set(), set()
        for model, key, ep in combos:
            if len(chosen) >= self.top_k:
                break
            if model in used_models:
                continue
            chosen.append((model, key, ep))
            used_models.add(model)
            used_eps.add(id(ep))
        # Fill remaining slots with any leftover combos.
        for model, key, ep in combos:
            if len(chosen) >= self.top_k:
                break
            if (model, id(ep)) in {(m, id(e)) for m, _, e in chosen}:
                continue
            chosen.append((model, key, ep))

        messages = self._messages(system, prompt)
        texts: List[str] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(chosen)) as pool:
            futures = {
                pool.submit(self._post, ep, messages, model, key, temperature, None): (model, ep.base_url)
                for model, key, ep in chosen
            }
            for fut in concurrent.futures.as_completed(futures):
                model, base = futures[fut]
                try:
                    text = fut.result(timeout=self.timeout + 30)
                    if text:
                        texts.append(text)
                    else:
                        print(f"[llm] {model} @ {base}: empty response", file=sys.stderr)
                except Exception as e:
                    print(f"[llm] {model} @ {base}: {type(e).__name__}: {e}", file=sys.stderr)
        return texts

    def _merge_json(self, parsed: List[Any]) -> Any:
        """Consensus merge for ensemble JSON responses."""
        # Findings-style responses (review agent): merge by fingerprint.
        if all(isinstance(p, dict) and "findings" in p for p in parsed):
            return self._merge_findings_responses(parsed)
        # List responses (plans, task lists): union + dedupe by json equality.
        if all(isinstance(p, list) for p in parsed):
            return self._merge_lists(parsed)
        # Scalar-dict responses: majority vote per top-level key.
        if all(isinstance(p, dict) for p in parsed):
            return self._merge_scalar_dicts(parsed)
        # Mixed: return the most confident dict, else first parseable.
        return parsed[0]

    def _merge_findings_responses(self, parsed: List[Dict]) -> Dict:
        buckets: Dict[str, List[Dict]] = {}
        summaries = []
        for resp in parsed:
            if isinstance(resp.get("summary"), str):
                summaries.append(resp["summary"])
            for f in resp.get("findings", []) or []:
                if not isinstance(f, dict) or not f.get("path"):
                    continue
                path = f.get("path")
                line = f.get("line")
                suggestion = f.get("suggestion") or f.get("message")
                fp = _fp(path, line, suggestion)
                f["_fp"] = fp
                f["_agreement"] = 1
                buckets.setdefault(fp, []).append(f)

        merged_findings = []
        for fp, items in buckets.items():
            agreement = len(items)
            confs = []
            for f in items:
                try:
                    confs.append(float(f.get("confidence", 0.5)))
                except (TypeError, ValueError):
                    confs.append(0.5)
            best_conf = max(confs)
            if agreement >= self.min_agreement or best_conf >= self.high_confidence:
                best = max(items, key=lambda f: _conf(f))
                best["confidence"] = max(best_conf, 0.7)  # agreement bonus
                best["_agreement"] = agreement
                best.pop("_fp", None)
                merged_findings.append(best)

        summary = " | ".join(dict.fromkeys(s for s in summaries if s))[:2000]
        return {"summary": summary, "findings": merged_findings}

    def _merge_lists(self, parsed: List[list]) -> List[Any]:
        out: List[Any] = []
        seen = set()
        for item in [i for lst in parsed for i in lst]:
            key = json.dumps(item, sort_keys=True, default=str)
            if key not in seen:
                seen.add(key)
                out.append(item)
        return out

    def _merge_scalar_dicts(self, parsed: List[Dict]) -> Dict:
        from collections import Counter
        keys = set()
        for p in parsed:
            keys.update(p.keys())
        merged: Dict[str, Any] = {}
        for key in keys:
            vals = Counter()
            best_val, best_conf = None, -1.0
            for p in parsed:
                if key not in p:
                    continue
                val = p[key]
                if isinstance(val, (dict, list)):
                    best_val, best_conf = val, 1.0
                    continue
                try:
                    vals[repr(val)] += 1
                except Exception:
                    vals[repr(val)] = 1
                try:
                    conf = float(p.get("confidence", 0.5))
                except (TypeError, ValueError):
                    conf = 0.5
                if conf > best_conf:
                    best_conf, best_val = conf, val
            if vals:
                winner = max(vals.items(), key=lambda kv: kv[1])
                merged[key] = eval(winner[0]) if _is_scalar_literal(winner[0]) else winner[0]
            else:
                merged[key] = best_val
        return merged

    # ── Internals ───────────────────────────────────────────────────────────

    @staticmethod
    def _messages(system: Optional[str], prompt: str) -> List[Dict]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _all_combos(self) -> List[Tuple[str, str, Endpoint]]:
        combos = []
        for ep in self.endpoints:
            for model, key in ep.combos():
                combos.append((model, key, ep))
        return combos

    def _post(self, ep: Endpoint, messages, model: str, key: Optional[str],
              temperature, max_tokens) -> Optional[str]:
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        temp = temperature if temperature is not None else self.temperature
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temp,
            "max_tokens": max_tokens or ep.max_tokens or self.max_tokens,
            "options": {"temperature": temp},
        }
        resp = requests.post(
            f"{ep.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=ep.timeout or self.timeout,
        )
        if resp.status_code in (401, 403):
            raise ProviderError(f"auth failed for {model}: {resp.status_code}")
        if resp.status_code == 429:
            raise RateLimited(f"rate limited on {model}: {resp.status_code}")
        if resp.status_code >= 500:
            raise ProviderError(f"server error on {model}: {resp.status_code} {resp.text[:200]}")
        if resp.status_code != 200:
            raise ProviderError(f"unexpected status {resp.status_code}: {resp.text[:200]}")
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            raise ProviderError("malformed response payload")


# ── JSON extraction ──────────────────────────────────────────────────────────

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str):
    """Best-effort JSON extraction from a model response."""
    if not text:
        return None
    cleaned = text.strip()
    fenced = _FENCE_RE.findall(cleaned)
    candidates = list(fenced) + [cleaned]
    for cand in candidates:
        cand = cand.strip().strip("`").strip()
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass
    for start_char, end_char in (("{", "}"), ("[", "]")):
        start = cleaned.find(start_char)
        if start == -1:
            continue
        depth, in_str, escape = 0, False, False
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == start_char:
                depth += 1
            elif ch == end_char:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(cleaned[start:i + 1])
                    except json.JSONDecodeError:
                        break
    return None


def _fp(path: str, line: Optional[int], suggestion: Optional[str]) -> str:
    import hashlib
    base = f"{path}:{line or 0}"
    if suggestion:
        base += "|" + str(suggestion).strip()[:200]
    return hashlib.sha256(base.encode("utf-8", errors="ignore")).hexdigest()


def _conf(f: Dict) -> float:
    try:
        return float(f.get("confidence", 0.5))
    except (TypeError, ValueError):
        return 0.5


def _is_scalar_literal(repr_val: str) -> bool:
    try:
        json.loads(repr_val)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


if __name__ == "__main__":
    client = LLMClient()
    print(client.describe())
    print("JSON parse smoke test:", extract_json('```json\n{"a": 1}\n```'))
    merged = client._merge_json([
        {"summary": "two bugs", "findings": [
            {"path": "a.py", "line": 3, "severity": "critical", "message": "null deref", "confidence": 0.9},
            {"path": "b.py", "line": 1, "severity": "minor", "message": "nit", "confidence": 0.6},
        ]},
        {"summary": "two bugs", "findings": [
            {"path": "a.py", "line": 3, "severity": "critical", "message": "null deref", "confidence": 0.95},
        ]},
    ])
    print("Ensemble merge test:", json.dumps(merged["findings"]))
