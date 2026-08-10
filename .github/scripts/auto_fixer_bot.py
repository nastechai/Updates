#!/usr/bin/env python3
import os
import sys
import json
import base64
import requests
import subprocess

# Configuration
OLLAMA_API_BASE = "https://ollama.com/v1"
MODELS = ["gemma:31b", "codellama:34b", "llama3:70b"]
KEYS = [
    os.environ.get("OLLAMA_API_KEY_1"),
    os.environ.get("OLLAMA_API_KEY_2"),
    os.environ.get("OLLAMA_API_KEY_3")
]
GITHUB_TOKEN = os.environ.get("NAS_TOKEN") or os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY")

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
    
    # Token optimization: Limit max tokens and use system prompt
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an expert DevOps engineer. Provide a JSON response with 'fix_description' and 'files_to_update' (a list of objects with 'path' and 'content'). Only provide the JSON."},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "options": {
            "num_predict": 2048,
            "temperature": 0.2
        }
    }
    
    try:
        response = requests.post(f"{OLLAMA_API_BASE}/chat/completions", headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        elif response.status_code == 429: # Rate limit
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
        data = json.loads(fix_json)
        print(f"Applying fix: {data.get('fix_description')}")
        for file_fix in data.get('files_to_update', []):
            path = file_fix['path']
            content = file_fix['content']
            with open(path, 'w') as f:
                f.write(content)
            print(f"  Updated: {path}")
        return True
    except Exception as e:
        print(f"Failed to parse or apply fix: {e}")
        return False

def main():
    log_file = "FAILURE_REPORT.md"
    if not os.path.exists(log_file):
        print("No failure report found. Nothing to fix.")
        return

    with open(log_file, 'r') as f:
        failure_context = f.read()

    prompt = f"The following GitHub Action pipeline failed. Analyze the logs and provide a fix:\n\n{failure_context}"
    
    fix_content = call_ollama(prompt)
    if fix_content:
        # Extract JSON if model added markdown markers
        if "```json" in fix_content:
            fix_content = fix_content.split("```json")[1].split("```")[0].strip()
        
        if apply_fix(fix_content):
            print("Fix applied successfully.")
        else:
            print("Failed to apply fix.")
    else:
        print("Could not generate a fix.")

if __name__ == "__main__":
    main()
