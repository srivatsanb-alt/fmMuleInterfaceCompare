#!/usr/bin/env python3
"""
Fleet Manager → Mule Dependency Analysis Orchestrator

Automatically runs analyzers, generates reports, packages artifacts,
and optionally compares with parent commit.
"""
import os
import sys
import json
import subprocess
from pathlib import Path
from datetime import datetime


def run_command(cmd: list, description: str = "") -> bool:
    """Run a shell command and return success status."""
    if description:
        print(f"\nRUN: {description}")
    try:
        result = subprocess.run(cmd, capture_output=False, text=True, cwd=os.getcwd())
        return result.returncode == 0
    except Exception as e:
        print(f"Error running {cmd}: {e}")
        return False


def get_current_commit_hash() -> str:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        return result.stdout.strip()[:12] if result.returncode == 0 else "unknown"
    except:
        return "unknown"


def get_current_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except:
        return "unknown"


def get_current_version() -> str:
    """Get version from pyproject.toml."""
    try:
        with open("pyproject.toml", "r") as f:
            for line in f:
                if line.startswith("version"):
                    # Extract version from: version = "1.0.0"
                    parts = line.split("=")
                    if len(parts) > 1:
                        return parts[1].strip().strip('"').strip("'")
    except:
        pass
    return "unknown"


def generate_timestamp() -> str:
    """Generate ISO timestamp for artifact naming."""
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def main():
    repo_root = Path(os.getcwd())
    timestamp = generate_timestamp()
    commit_hash = get_current_commit_hash()
    branch = get_current_branch()
    version = get_current_version()
    
    artifact_suffix = f"{branch}-{commit_hash}-{timestamp}"
    
    print("="*60)
    print("Fleet Manager → Mule Dependency Analysis")
    print("="*60)
    print(f"Repository: {repo_root.name}")
    print(f"Branch: {branch}")
    print(f"Commit: {commit_hash}")
    print(f"Version: {version}")
    print(f"Timestamp: {timestamp}")
    
    # Create output directories
    os.makedirs("docs/dep_graphs", exist_ok=True)
    os.makedirs("packages/reports", exist_ok=True)
    
    # Step 1: Run simple dependency analyzer
    print("\n" + "="*60)
    print("STEP 1: Running simple dependency analyzer...")
    run_command(
        [sys.executable, "scripts/analyze_mule_deps.py"],
        "python3 scripts/analyze_mule_deps.py"
    )
    
    # Step 2: Run detailed dependency analyzer (produces JSON)
    print("\n" + "="*60)
    print("STEP 2: Running detailed dependency analyzer (JSON output)...")
    detailed_report = f"docs/dep_graphs/fleet_manager_mule_detailed_analysis.json"
    run_command(
        [sys.executable, "scripts/analyze_detailed_mule_deps.py", ".", "mule"],
        f"python3 scripts/analyze_detailed_mule_deps.py . mule"
    )
    
    # Step 3: Generate pyreverse diagrams
    print("\n" + "="*60)
    print("STEP 3: Generating Pyreverse diagrams...")
    
    if os.path.exists("scripts/gen_pyreverse_from_valid_files.py"):
        run_command(
            [sys.executable, "scripts/gen_pyreverse_from_valid_files.py", ".", "mule", "svg"],
            "python3 scripts/gen_pyreverse_from_valid_files.py . mule svg"
        )
    
    if os.path.exists("scripts/gen_fm_on_mule_pyreverse.py"):
        run_command(
            [sys.executable, "scripts/gen_fm_on_mule_pyreverse.py", ".", "svg"],
            "python3 scripts/gen_fm_on_mule_pyreverse.py . svg"
        )
    
    # Step 4: Create report package
    print("\n" + "="*60)
    print("STEP 4: Packaging reports...")
    
    report_package = f"packages/reports/reports-{version}-{artifact_suffix}.tar.gz"
    report_manifest = f"packages/reports/reports-{version}-{artifact_suffix}.manifest.json"
    
    # Create manifest
    manifest = {
        "version": version,
        "branch": branch,
        "commit": commit_hash,
        "generated_at": timestamp,
        "files": [
            "docs/dep_graphs/fleet_manager_mule_detailed_analysis.json",
            "docs/dep_graphs/mule_dependency_analysis.md",
            "docs/dep_graphs/classes_mule.svg",
            "docs/dep_graphs/packages_mule.svg",
            "docs/dep_graphs/classes_fleet_manager_on_mule.svg",
            "docs/dep_graphs/packages_fleet_manager_on_mule.svg"
        ]
    }
    
    # Filter existing files
    manifest["files"] = [f for f in manifest["files"] if os.path.exists(f)]
    
    with open(report_manifest, "w") as f:
        json.dump(manifest, f, indent=2)
    
    # Create tarball
    files_to_tar = " ".join(manifest["files"])
    tar_cmd = f"tar -czf {report_package} {files_to_tar}"
    try:
        subprocess.run(tar_cmd, shell=True, check=True, cwd=repo_root)
        print(f"✓ Report package created: {report_package}")
    except:
        print(f"⚠ Failed to create report package")
    
    # Step 5: Optional comparison with parent commit
    print("\n" + "="*60)
    print("STEP 5: Checking for parent commit report...")
    
    try:
        parent_commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        if parent_commit_result.returncode == 0:
            parent_commit = parent_commit_result.stdout.strip()[:12]
            parent_report = None
            
            # Look for parent commit report in packages/reports
            for report_file in Path("packages/reports").glob("*.json"):
                if parent_commit in str(report_file) and "manifest" not in str(report_file):
                    parent_report = str(report_file)
                    break
            
            if parent_report and os.path.exists(parent_report):
                print(f"Found parent commit report: {parent_report}")
                
                # Run comparison
                comparison_output = f"docs/dep_graphs/comparison-{artifact_suffix}.json"
                comparison_md = f"docs/dep_graphs/comparison-{artifact_suffix}.md"
                
                if os.path.exists("scripts/compare_dep_reports.py"):
                    run_command(
                        [sys.executable, "scripts/compare_dep_reports.py", 
                         parent_report, detailed_report, 
                         comparison_output, comparison_md],
                        f"python3 scripts/compare_dep_reports.py {parent_report} {detailed_report}"
                    )
                    print(f"✓ Comparison saved to: {comparison_output}")
                    print(f"✓ Comparison markdown: {comparison_md}")
            else:
                print("No parent commit report found (first commit or parent reports not archived)")
    except Exception as e:
        print(f"Note: Could not check parent commit: {e}")
    
    print("\n" + "="*60)
    print("✓ Fleet Manager → Mule dependency analysis complete!")
    print("="*60)
    print("\nGenerated artifacts:")
    print(f"  - JSON Report: {detailed_report}")
    print(f"  - Report Package: {report_package}")
    print(f"  - Package Manifest: {report_manifest}")
    print("\nTo compare with a previous report:")
    print(f"  python3 scripts/compare_dep_reports.py <old_report.json> {detailed_report}")


if __name__ == "__main__":
    main()
