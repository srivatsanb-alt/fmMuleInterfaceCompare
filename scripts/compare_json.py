import json
import sys

def compare_snapshots(base_file, head_file):
    with open(base_file) as f: base = json.load(f)
    with open(head_file) as f: head = json.load(f)

    diffs = []
    all_files = set(base.keys()) | set(head.keys())

    for file in all_files:
        base_funcs = set(base.get(file, []))
        head_funcs = set(head.get(file, []))
        
        removed = base_funcs - head_funcs
        added = head_funcs - base_funcs

        if removed: diffs.append(f"| `{file}` | Removed | {', '.join(removed)} | 🔴 High |")
        if added: diffs.append(f"| `{file}` | Added | {', '.join(added)} | 🟡 Low |")

    if diffs:
        print("### 🔍 Interface Delta Report")
        print("| File | Change | Functions | Risk Level |")
        print("| :--- | :--- | :--- | :--- |")
        print("\n".join(diffs))
        sys.exit(1) # Fail the check
    else:
        print("✅ No interface changes detected.")
        sys.exit(0)

if __name__ == "__main__":
    compare_snapshots(sys.argv[1], sys.argv[2])