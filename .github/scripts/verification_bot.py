#!/usr/bin/env python3
import os
import sys
import json
import re
import subprocess
from pathlib import Path

class VerificationBot:
    def __init__(self, repo_root="."):
        self.repo_root = Path(repo_root).resolve()
        self.rules = [
            (r"hermes-agent", "nastech-agent"),
            (r"Hermes Agent", "NasTech Agent"),
            (r"@nous-research", "@nastech-research"),
            (r"nousresearch", "nastechairesearch"),
            (r"NousResearch", "nastechai"),
            (r"HERMES_", "NASTECH_"),
            (r"hermes", "nastech"),
            (r"Hermes", "NasTech"),
        ]
        self.exclude_dirs = {".git", "node_modules", ".venv", "dist", "build", ".github/workflows"}
        self.results = {
            "branding_score": 0,
            "test_score": 0,
            "total_score": 0,
            "violations": [],
            "passed_tests": 0,
            "failed_tests": 0,
            "status": "FAIL"
        }

    def check_branding(self):
        total_checks = 0
        violations = 0
        
        for root, dirs, files in os.walk(self.repo_root):
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.json', '.yml', '.yaml', '.md', '.sh')):
                    filepath = Path(root) / file
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for pattern, _ in self.rules:
                                matches = re.findall(pattern, content)
                                if matches:
                                    violations += len(matches)
                                    self.results["violations"].append({
                                        "file": str(filepath.relative_to(self.repo_root)),
                                        "pattern": pattern,
                                        "count": len(matches)
                                    })
                                total_checks += 1
                    except Exception:
                        pass
        
        # Calculate score: 100 - (violations / total_checks * 100) if checks exist
        if total_checks > 0:
            self.results["branding_score"] = max(0, 100 - (violations / total_checks * 100))
        else:
            self.results["branding_score"] = 100

    def run_branded_tests(self):
        # Look for tests in the tests/ directory
        test_dir = self.repo_root / "tests"
        if not test_dir.exists():
            self.results["test_score"] = 100 # No tests to fail
            return

        try:
            # We assume pytest or a simple python runner
            result = subprocess.run(["python3", "-m", "pytest", str(test_dir), "--json-report", "--json-report-file=/tmp/test_report.json"], 
                                    capture_output=True, text=True)
            
            if os.path.exists("/tmp/test_report.json"):
                with open("/tmp/test_report.json", "r") as f:
                    data = json.load(f)
                    summary = data.get("summary", {})
                    passed = summary.get("passed", 0)
                    total = summary.get("total", 0)
                    self.results["passed_tests"] = passed
                    self.results["failed_tests"] = total - passed
                    if total > 0:
                        self.results["test_score"] = (passed / total) * 100
                    else:
                        self.results["test_score"] = 100
            else:
                # Fallback to exit code
                if result.returncode == 0:
                    self.results["test_score"] = 100
                else:
                    self.results["test_score"] = 0
        except Exception as e:
            print(f"Error running tests: {e}")
            self.results["test_score"] = 0

    def analyze(self, threshold=80):
        self.check_branding()
        self.run_branded_tests()
        
        self.results["total_score"] = (self.results["branding_score"] + self.results["test_score"]) / 2
        
        if self.results["total_score"] >= threshold:
            self.results["status"] = "PASS"
        else:
            self.results["status"] = "FAIL"
            
        return self.results

if __name__ == "__main__":
    bot = VerificationBot()
    threshold = int(sys.argv[1]) if len(sys.argv) > 1 else 80
    report = bot.analyze(threshold)
    
    # Save report
    with open("VERIFICATION_REPORT.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Print summary for logs
    print(f"--- NasTech Verification Bot ---")
    print(f"Branding Score: {report['branding_score']:.2f}%")
    print(f"Test Score:     {report['test_score']:.2f}%")
    print(f"Total Score:    {report['total_score']:.2f}%")
    print(f"Threshold:      {threshold}%")
    print(f"Status:         {report['status']}")
    
    if report["status"] == "FAIL":
        print("\nViolations Found:")
        for v in report["violations"][:10]: # Show first 10
            print(f"- {v['file']}: Found '{v['pattern']}' ({v['count']} times)")
        sys.exit(1)
    else:
        sys.exit(0)
