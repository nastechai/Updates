#!/usr/bin/env python3
import os
import sys
import json
import base64
import requests
import subprocess

# Configuration
OLLAMA_API_BASE = "https://ollama.com/v1"
MODELS = ["gemma4:31b", "kimi-k2.7-code", "deepseek-v4-pro", "mistral-large-3:675b"]
KEYS = [
    os.environ.get("OLLAMA_API_KEY_1"),
    os.environ.get("OLLAMA_API_KEY_2"),
    os.environ.get("OLLAMA_API_KEY_3")
]
GITHUB_TOKEN = os.environ.get("NAS_TOKEN") or os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY")

# Strict Constraints from User & AGENTS.md
SYSTEM_PROMPT = """You are the NasTech Auto-Fixer Bot. Your absolute mandate is to maintain 100% alignment with the Hermes (Nous Research) agent architecture and logic while preserving NasTech branding.

STRICT RULES:
1. FOLLOW AGENTS.md: You must adhere to all rules in AGENTS.md (e.g., no change-detector tests, no reading source code in tests, proper pytest markers).
2. HERMES LOGIC ONLY: Do not add any new features, coding, or logic that does not exist in the original Hermes (hermes-agent) source. If a fix is needed, it must be the 'Hermes way'.
3. NO BRANDING FIXES: Do not attempt to 'fix' branding or rename things unless it is a direct result of a code error. The branding pipeline handles transformation; you handle code integrity.
4. MATCH HERMES BUT NASTECH: The code logic must be identical to Hermes, but using NasTech/nastech names as defined by the branding rules.
5. JSON ONLY: Provide your response as a raw JSON object with 'fix_description' and 'files_to_update' (list of {'path', 'content'}).

Your goal is to fix pipeline failures by restoring or correcting code to match the Hermes standard."""

def call_ollama(prompt, model_index=0, key_index=0):
    if key_index >= len(KEYS) or not KEYS[key_index]:
        print("No more valid API keys.")
        return None
    
    if model_index >= len(MODELS):
        print("All models failed.")
        return None

    model = MODELS[model_index]
    key = KEYS[key_index]
    
    print(f"Attempting fix with model: {model} using Key {key_index+1}")
    
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    # Token optimization: Limit max tokens and use strict system prompt
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": 0.1 # Lower temperature for stricter adherence
        }
    }
    
    try:
        response = requests.post(f"{OLLAMA_API_BASE}/chat/completions", headers=headers, json=payload, timeout=90)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        elif response.status_code == 429:
            print("Rate limited. Switching key...")
            return call_ollama(prompt, model_index, key_index + 1)
        else:
            print(f"Error {response.status_code}: {response.text}")
            return call_ollama(prompt, model_index + 1, key_index)
    except Exception as e:
        print(f"Request failed: {e}")
        return call_ollama(prompt, model_index + 1, key_index)

def apply_fix(fix_json):
    try:
        # Clean up markdown if present
        if "```json" in fix_json:
            fix_json = fix_json.split("```json")[1].split("```")[0].strip()
        elif "```" in fix_json:
            fix_json = fix_json.split("```")[1].split("```")[0].strip()
            
        data = json.loads(fix_json.strip())
        print(f"Applying fix: {data.get('fix_description')}")
        for file_fix in data.get('files_to_update', []):
            path = file_fix['path']
            content = file_fix['content']
            
            # Ensure path is safe
            if ".." in path or path.startswith("/"):
                print(f"  REJECTED (unsafe path): {path}")
                continue
                
            with open(path, 'w') as f:
                f.write(content)
            print(f"  Updated: {path}")
        return True
    except Exception as e:
        print(f"Failed to parse or apply fix: {e}")
        print(f"Raw output was: {fix_json[:500]}...")
        return False

def main():
    log_file = "FAILURE_REPORT.md"
    if not os.path.exists(log_file):
        # Try finding any .md or .log files if specific report is missing
        print("Specific FAILURE_REPORT.md not found. Checking for context...")
        failure_context = "No specific log file found, but the pipeline failed."
    else:
        with open(log_file, 'r') as f:
            failure_context = f.read()

    # Add AGENTS.md content to prompt for context
    agents_md = ""
    if os.path.exists("AGENTS.md"):
        with open("AGENTS.md", "r") as f:
            agents_md = f.read()[:2000] # First 2k chars for context

    prompt = f"### AGENTS.md Rules:\n{agents_md}\n\n### Failure Context:\n{failure_context}\n\nProvide the fix following the strict Hermes-alignment rules."
    
    fix_content = call_ollama(prompt)
    if fix_content:
        if apply_fix(fix_content):
            print("Fix applied successfully.")
        else:
            sys.exit(1)
    else:
        print("Could not generate a fix.")
        sys.exit(1)

if __name__ == "__main__":
    main()
