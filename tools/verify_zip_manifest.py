import hashlib
import os
import shutil
import tempfile
import zipfile

zip_path = r"D:\JARVIS-AI\release\JARVIS_Mark_LVI_Windows_x64_Portable.zip"
manifest_path = r"D:\JARVIS-AI\release\SHA256_MANIFEST.txt"

# Read expected manifest
expected = {}
with open(manifest_path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        parts = line.split("  ", 1)
        if len(parts) == 2:
            expected[parts[1].replace("/", "\\")] = parts[0]

temp_dir = tempfile.mkdtemp(prefix="jarvis_zip_test_")
print(f"Extracting {zip_path} into {temp_dir}...")

try:
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(temp_dir)

    matched = 0
    mismatched = 0
    missing = 0

    for rel_path, expected_hash in expected.items():
        extracted_file = os.path.join(temp_dir, rel_path)
        if not os.path.exists(extracted_file):
            print(f"MISSING: {rel_path}")
            missing += 1
            continue
        with open(extracted_file, "rb") as fh:
            actual_hash = hashlib.sha256(fh.read()).hexdigest()
        if actual_hash == expected_hash:
            matched += 1
        else:
            print(f"MISMATCH: {rel_path} (Expected {expected_hash}, got {actual_hash})")
            mismatched += 1

    print(f"\nRESULTS:")
    print(f"Total Expected Files: {len(expected)}")
    print(f"Matched 100%: {matched}")
    print(f"Mismatched: {mismatched}")
    print(f"Missing: {missing}")

    if matched == len(expected) and mismatched == 0 and missing == 0:
        print("\nSUCCESS: 100% Manifest Integrity Verified!")
    else:
        print("\nFAILURE: Manifest discrepancies found!")
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
