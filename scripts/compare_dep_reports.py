#!/usr/bin/env python3
"""
Compare two dependency analysis JSON reports for changes.
Useful for detecting interface changes, new usages, or removed integrations.
"""
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict


def load_report(filepath: str) -> Dict:
    """Load a JSON dependency report."""
    with open(filepath, 'r') as f:
        return json.load(f)


def compare_statistics(old_stats: Dict, new_stats: Dict) -> Dict:
    """Compare statistics between two reports."""
    changes = {}
    for key in new_stats:
        if key in old_stats:
            old_val = old_stats[key]
            new_val = new_stats[key]
            if old_val != new_val:
                changes[key] = {
                    "old": old_val,
                    "new": new_val,
                    "delta": new_val - old_val if isinstance(new_val, int) else None
                }
    return changes


def compare_interface_calls(old_calls: Dict, new_calls: Dict) -> Dict:
    """Compare interface calls between reports."""
    comparison = {
        "removed": [],
        "added": [],
        "modified": []
    }
    
    old_interfaces = set(old_calls.keys())
    new_interfaces = set(new_calls.keys())
    
    # Removed interfaces
    for iface in old_interfaces - new_interfaces:
        comparison["removed"].append({
            "interface": iface,
            "old_usage_count": old_calls[iface]["usage_count"],
            "usage_locations": old_calls[iface]["usage_locations"]
        })
    
    # Added interfaces
    for iface in new_interfaces - old_interfaces:
        comparison["added"].append({
            "interface": iface,
            "new_usage_count": new_calls[iface]["usage_count"],
            "usage_locations": new_calls[iface]["usage_locations"]
        })
    
    # Modified interfaces (usage count changed)
    for iface in old_interfaces & new_interfaces:
        old_usage = old_calls[iface]["usage_count"]
        new_usage = new_calls[iface]["usage_count"]
        if old_usage != new_usage:
            old_locations = {(u["file"], u["line"]) for u in old_calls[iface]["usage_locations"]}
            new_locations = {(u["file"], u["line"]) for u in new_calls[iface]["usage_locations"]}
            
            comparison["modified"].append({
                "interface": iface,
                "old_usage_count": old_usage,
                "new_usage_count": new_usage,
                "delta": new_usage - old_usage,
                "new_usage_locations": [u for u in new_calls[iface]["usage_locations"] 
                                       if (u["file"], u["line"]) not in old_locations],
                "removed_usage_locations": [u for u in old_calls[iface]["usage_locations"] 
                                           if (u["file"], u["line"]) not in new_locations]
            })
    
    return comparison


def compare_files(old_files: Dict, new_files: Dict) -> Dict:
    """Compare importing files between reports."""
    comparison = {
        "new_importers": [],
        "removed_importers": [],
        "changed_imports": []
    }
    
    old_file_set = set(old_files.keys())
    new_file_set = set(new_files.keys())
    
    # New importers
    for file_path in new_file_set - old_file_set:
        comparison["new_importers"].append({
            "file": file_path,
            "imports": new_files[file_path]["imports"]
        })
    
    # Removed importers
    for file_path in old_file_set - new_file_set:
        comparison["removed_importers"].append({
            "file": file_path,
            "imports": old_files[file_path]["imports"]
        })
    
    # Changed imports
    for file_path in old_file_set & new_file_set:
        old_imports = set(old_files[file_path]["imports"])
        new_imports = set(new_files[file_path]["imports"])
        if old_imports != new_imports:
            comparison["changed_imports"].append({
                "file": file_path,
                "added_imports": sorted(list(new_imports - old_imports)),
                "removed_imports": sorted(list(old_imports - new_imports))
            })
    
    return comparison


def generate_comparison_report(old_report: Dict, new_report: Dict) -> Dict:
    """Generate a comprehensive comparison report."""
    report = {
        "metadata": {
            "version": "1.0",
            "old_report_generated": old_report.get("metadata", {}).get("generated_at"),
            "new_report_generated": new_report.get("metadata", {}).get("generated_at")
        },
        "summary": {
            "statistic_changes": compare_statistics(
                old_report.get("statistics", {}),
                new_report.get("statistics", {})
            ),
            "interface_changes_count": 0,
            "file_changes_count": 0
        },
        "interface_calls": compare_interface_calls(
            old_report.get("fleet_manager_usage", {}).get("interface_calls", {}),
            new_report.get("fleet_manager_usage", {}).get("interface_calls", {})
        ),
        "importing_files": compare_files(
            old_report.get("fleet_manager_usage", {}).get("importing_files", {}),
            new_report.get("fleet_manager_usage", {}).get("importing_files", {})
        )
    }
    
    # Calculate change counts
    interface_comp = report["interface_calls"]
    file_comp = report["importing_files"]
    
    report["summary"]["interface_changes_count"] = (
        len(interface_comp["added"]) + 
        len(interface_comp["removed"]) + 
        len(interface_comp["modified"])
    )
    report["summary"]["file_changes_count"] = (
        len(file_comp["new_importers"]) + 
        len(file_comp["removed_importers"]) + 
        len(file_comp["changed_imports"])
    )
    
    return report


def format_comparison_report(comparison: Dict) -> str:
    """Format comparison report as human-readable text."""
    lines = []
    
    lines.append("# Dependency Report Comparison\n")
    
    # Metadata
    meta = comparison.get("metadata", {})
    lines.append("## Comparison Timeline")
    lines.append(f"- Old report: {meta.get('old_report_generated', 'N/A')}")
    lines.append(f"- New report: {meta.get('new_report_generated', 'N/A')}\n")
    
    # Summary
    summary = comparison.get("summary", {})
    lines.append("## Summary of Changes")
    lines.append(f"- Interface changes: {summary.get('interface_changes_count', 0)}")
    lines.append(f"- File changes: {summary.get('file_changes_count', 0)}")
    
    stat_changes = summary.get("statistic_changes", {})
    if stat_changes:
        lines.append("\n### Statistic Changes")
        for key, change in sorted(stat_changes.items()):
            old = change.get("old")
            new = change.get("new")
            delta = change.get("delta")
            if delta is not None:
                lines.append(f"- {key}: {old} → {new} (delta: {delta:+d})")
            else:
                lines.append(f"- {key}: {old} → {new}")
    
    # Interface changes
    interfaces = comparison.get("interface_calls", {})
    
    if interfaces.get("added"):
        lines.append("\n## New Interfaces Used")
        for item in interfaces["added"]:
            lines.append(f"\n### `{item['interface']}`")
            lines.append(f"- Usage count: {item['new_usage_count']}")
            lines.append("- Locations:")
            for usage in item["usage_locations"]:
                lines.append(f"  - {usage['file']}:{usage['line']} in `{usage['caller']}`")
                lines.append(f"    Call: `{item['interface']}({usage['call_args']})`")
    
    if interfaces.get("removed"):
        lines.append("\n## Removed Interfaces")
        for item in interfaces["removed"]:
            lines.append(f"\n### `{item['interface']}`")
            lines.append(f"- Was used {item['old_usage_count']} time(s)")
            lines.append("- Previously at:")
            for usage in item["usage_locations"]:
                lines.append(f"  - {usage['file']}:{usage['line']} in `{usage['caller']}`")
    
    if interfaces.get("modified"):
        lines.append("\n## Modified Interfaces")
        for item in interfaces["modified"]:
            lines.append(f"\n### `{item['interface']}`")
            lines.append(f"- Usage count: {item['old_usage_count']} → {item['new_usage_count']} (delta: {item['delta']:+d})")
            
            if item.get("new_usage_locations"):
                lines.append("- New usage locations:")
                for usage in item["new_usage_locations"]:
                    lines.append(f"  - {usage['file']}:{usage['line']} in `{usage['caller']}`")
                    lines.append(f"    Call: `{item['interface']}({usage['call_args']})`")
            
            if item.get("removed_usage_locations"):
                lines.append("- Removed usage locations:")
                for usage in item["removed_usage_locations"]:
                    lines.append(f"  - {usage['file']}:{usage['line']} in `{usage['caller']}`")
    
    # File changes
    files = comparison.get("importing_files", {})
    
    if files.get("new_importers"):
        lines.append("\n## New Files Importing Mule")
        for item in files["new_importers"]:
            lines.append(f"\n- **{item['file']}**")
            lines.append(f"  - Imports: {', '.join(item['imports'])}")
    
    if files.get("removed_importers"):
        lines.append("\n## Files No Longer Importing Mule")
        for item in files["removed_importers"]:
            lines.append(f"\n- **{item['file']}**")
            lines.append(f"  - Was importing: {', '.join(item['imports'])}")
    
    if files.get("changed_imports"):
        lines.append("\n## Changed Imports")
        for item in files["changed_imports"]:
            lines.append(f"\n- **{item['file']}**")
            if item.get("added_imports"):
                lines.append(f"  - Added: {', '.join(item['added_imports'])}")
            if item.get("removed_imports"):
                lines.append(f"  - Removed: {', '.join(item['removed_imports'])}")
    
    return "\n".join(lines)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 compare_dep_reports.py <old_report.json> <new_report.json> [output.json] [output.md]")
        print("\nCompare two dependency analysis reports and detect changes.")
        sys.exit(1)
    
    old_report_path = sys.argv[1]
    new_report_path = sys.argv[2]
    output_json = sys.argv[3] if len(sys.argv) > 3 else None
    output_md = sys.argv[4] if len(sys.argv) > 4 else None
    
    # Load reports
    print(f"Loading old report: {old_report_path}")
    old_report = load_report(old_report_path)
    
    print(f"Loading new report: {new_report_path}")
    new_report = load_report(new_report_path)
    
    # Generate comparison
    print("Comparing reports...")
    comparison = generate_comparison_report(old_report, new_report)
    
    # Output JSON comparison
    if output_json:
        with open(output_json, 'w') as f:
            json.dump(comparison, f, indent=2)
        print(f"✓ JSON comparison saved to: {output_json}")
    else:
        print("\n" + "="*60)
        print(json.dumps(comparison, indent=2))
        print("="*60)
    
    # Output formatted comparison
    formatted = format_comparison_report(comparison)
    if output_md:
        with open(output_md, 'w') as f:
            f.write(formatted)
        print(f"✓ Formatted comparison saved to: {output_md}")
    else:
        print("\n" + formatted)
