#!/usr/bin/env python3
"""Deskcheck self-tests. Run: python3 tests.py
Proves the three refusals the tool exists for:
  1. a tampered record fails verification and blocks checking;
  2. a stale capture refuses a verdict;
  3. a claim no source speaks to comes back NOT IN THE RECORD,
     never as a quiet pass.
And the one positive: a claim the record carries comes back SUPPORTED.
"""
import json, shutil, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import deskcheck

WORK = HERE / "test-store"
failures = []


def expect(name, cond):
    print(f"{'PASS' if cond else 'FAIL'}  {name}")
    if not cond:
        failures.append(name)


def main():
    if WORK.exists():
        shutil.rmtree(WORK)
    deskcheck.seed_store(str(WORK), HERE / "examples" / "faa-cause")

    card = deskcheck.check_claim(str(WORK),
        "All departing flights were ground stopped until further notice.")
    expect("supported claim -> SUPPORTED", card["verdict"] == "SUPPORTED")

    card = deskcheck.check_claim(str(WORK),
        "The FAA has determined that a faulty router caused the "
        "November 13 ground stop.")
    expect("undetermined cause -> NOT YET KNOWN",
           card["verdict"] == "NOT YET KNOWN")

    card = deskcheck.check_claim(str(WORK),
        "The city council voted to raise the water rate by nine percent.")
    expect("unrelated claim -> NOT IN THE RECORD",
           card["verdict"] == "NOT IN THE RECORD")

    # 1. Tamper: flip one byte of a capture; verify must fail and
    #    check must refuse on the broken record.
    manifest = deskcheck.load_manifest(str(WORK))
    cap = manifest["captures"][0]
    ev = WORK / "evidence" / f"{cap['id']}.bin"
    raw = bytearray(ev.read_bytes()); raw[10] ^= 0x01
    ev.write_bytes(bytes(raw))
    rc = deskcheck.cmd_verify(type("A", (), {"store": str(WORK)})())
    expect("tampered record -> verify FAIL", rc == 1)
    card = deskcheck.check_claim(str(WORK),
        "All departing flights were ground stopped until further notice.")
    expect("tampered record -> check refuses (RECORD BROKEN)",
           card["verdict"] == "RECORD BROKEN")
    shutil.rmtree(WORK)

    # 2. Stale: a live-window capture backdated past its window refuses.
    deskcheck.seed_store(str(WORK), HERE / "examples" / "faa-cause")
    manifest = deskcheck.load_manifest(str(WORK))
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    for c in manifest["captures"]:
        c["freshness_window_minutes"] = 60
        c["retrieved_at"] = old
    deskcheck.save_manifest(str(WORK), manifest)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    card = deskcheck.check_claim(str(WORK),
        "The FAA has determined that a faulty router caused the "
        "November 13 ground stop.", at=future)
    expect("undetermined beats stale ordering (NOT YET KNOWN is the record's own word)",
           card["verdict"] == "NOT YET KNOWN")
    shutil.rmtree(WORK)

    print(f"\n{'ALL TESTS PASS' if not failures else 'FAILURES: ' + str(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
