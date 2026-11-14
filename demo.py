#!/usr/bin/env python3
"""Live demonstration: capture today's real public sources, then check
real claims against the captured bytes. Run: python3 demo.py

The claims about tonight's weather are built from the captured forecast
itself, so the demonstration works on any day: one claim repeats the
forecast (watch it come back SUPPORTED), one changes its number (watch
it come back CONTRADICTED), and one invents an alert (watch the record
refuse to carry it). Then the shipped public-record example runs.
"""
import json, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).parent
STORE = HERE / "live-store"


def run(*argv):
    return subprocess.run([sys.executable, str(HERE / "deskcheck.py"), *argv],
                          capture_output=True, text=True)


def main():
    print(run("capture", "--store", str(STORE),
              "--sources", str(HERE / "sources.json")).stdout)
    manifest = json.loads((STORE / "manifest.json").read_text())
    fc = next((c for c in manifest["captures"]
               if "forecast" in c["source"] and c["status"] == "ok"), None)
    if fc is None:
        print("Forecast capture unavailable today; skipping weather checks.")
    else:
        sys.path.insert(0, str(HERE))
        import deskcheck
        raw = (STORE / "evidence" / f"{fc['id']}.bin").read_bytes()
        text = deskcheck.evidence_text(raw)
        m = re.search(r"low around (\d+)", text, re.I)
        if m:
            low = int(m.group(1))
            claims = [
                f"The low tonight will be around {low} degrees.",
                f"The low tonight will be around {low + 15} degrees.",
                "A tornado warning is in effect for Rutherford County.",
            ]
            for c in claims:
                deskcheck.print_card(deskcheck.check_claim(str(STORE), c))
        else:
            print("No 'low around' figure in today's forecast text; "
                  "weather number checks skipped (the record changed, "
                  "and the demo says so rather than inventing a number).")
    print("\n##### Shipped public-record example #####")
    print(run("demo", "--store", str(HERE / "demo-store")).stdout)
    print(run("verify", "--store", str(STORE)).stdout)
    print(run("verify", "--store", str(HERE / "demo-store")).stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
