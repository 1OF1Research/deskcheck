# Deskcheck

**Check an official claim before you repeat it.**

Deskcheck is a free desk tool for small newsrooms, community radio,
library reference desks, and anyone whose job is to pass public
information on to their neighbors. You give it a claim — a sentence from
a press release, a post you are about to share, a line in a story you
are about to publish. It checks the claim against the official record it
has captured on your own machine and hands you back a **claim card**:

- the verdict the record actually supports,
- the exact words the source used, quoted verbatim,
- who the source is and where it lives,
- when your desk captured it,
- how fresh that capture is,
- and, when the record itself has not settled the matter, a verdict
  that says so in plain words — **NOT YET KNOWN** — together with
  what the record does say.

It runs entirely on your laptop. No account, no cloud, no subscription,
no AI model, no data about you or your readers ever leaves your desk.

## Why this exists

Small desks repeat official claims all day: the road is closed, the
water is safe, the school is open, the storm will miss us, the cause
was a faulty router. Most of those claims are true. The ones that are
not — or that are printed one day before the official record itself
says "not yet known" — do harm that a correction rarely undoes. A wrong
evacuation route, a wrong closure time, a cause stated as fact while
the investigators are still working: each one travels at the speed of
trust, and a local desk's trust is its whole capital.

The big platforms will not build this for a two-person newsroom or a
county library. It is too small for them. It is exactly the right size
for the desk itself — if the tool is small enough to run on the laptop
already sitting there, free enough to need no one's permission, and
honest enough to say *the record does not know yet* instead of guessing.

That is the whole design. If Deskcheck spreads, every public claim a
small desk repeats becomes checkable at its source, at zero cost per
check, forever. The value is not in the software. It is in every wrong
sentence that never gets repeated.

## Install

There is nothing to install. You need Python 3 (any recent version —
check with `python3 --version`). Deskcheck is one file,
`deskcheck.py`, using only Python's standard library. Download this
folder, keep it anywhere, and run it from that folder.

## Quickstart

```sh
# 1. Capture today's official sources into your evidence store.
python3 deskcheck.py capture

# 2. Check a claim against the captured record.
python3 deskcheck.py check "The low tonight will be around 27 degrees."

# 3. See how the record on a topic changed over time.
python3 deskcheck.py timeline cause ground stop

# 4. Re-verify your store — digests, verbatim passages, freshness.
python3 deskcheck.py verify

# 5. Run the shipped example: the November 2026 FAA ground stop,
#    including a claim the record honestly refuses to settle.
python3 deskcheck.py demo
python3 demo.py        # the full live demonstration (needs the network)
python3 tests.py       # the self-tests, including the tamper test
```

## How to read a claim card

| Verdict | What it means |
|---|---|
| **SUPPORTED** | Captured source text states the claim — including every number in it. |
| **CONTRADICTED ON THE NUMBERS** | Sources cover the subject but state different figures. The card shows what the record actually says. |
| **NOT IN THE RECORD** | No captured source states this claim. That is *not* proof it is false — it means this desk's record cannot carry it. Capture the source that would know, then check again. |
| **NOT YET KNOWN** | The record itself, on this very point, says the matter is not settled. The card shows what the record does say. Do not print the claim as fact. |
| **SOURCE STALE — REFUSED** | The only matching captures are older than their freshness window. Re-capture before relying on the check. |
| **RECORD BROKEN** | A capture no longer matches its recorded digest. The record itself cannot be trusted until the source is re-captured. |

Deskcheck never decides what is true. It shows what the record you
captured supports, quotes it verbatim, and refuses — out loud — when
the record cannot carry the claim. The judgment stays with the human
at the desk, where it belongs.

## Make it yours

Everything about Deskcheck is yours to change:

- **`sources.json`** is your source list. It ships with the sources a
  Rutherford County, Tennessee desk repeats — National Weather Service
  alerts and forecasts, FAA airspace status. Delete them. Add your own
  county's emergency feed, your city hall notices page, your school
  district's announcements, your state health department. Any public
  URL works.
- **Freshness windows** live in the same file, per source, in minutes.
  Weather alerts go stale in an hour; a forecast in six. Set each
  source's window to how fast that source can change its mind.
- **Your evidence store** is an ordinary folder (`store/`) of raw
  bytes plus a `manifest.json` you can read with any text editor.
  Copy it, back it up, hand it to a colleague, delete it. A claim card
  saved in `store/cards/` can be re-verified by anyone with this tool —
  that is how an editor checks a reporter's check.
- **The code** is one readable file. Fork it, translate it, adapt it
  to your language and your sources. It is MIT-licensed: yours.

## What it deliberately does not do

- It does not call any AI model, frontier or otherwise. Checking is
  deterministic: capture, digest, verbatim matching, freshness
  arithmetic. That is a design choice — a desk tool that must be
  trusted at deadline cannot depend on a service that can change,
  charge, or go down.
- It does not phone home. There is no server. There is nothing to
  sign up for and nothing to cancel.
- It does not scrape private sources or bypass anything. It reads the
  public sources you list, at the pace you run it.

## Feedback

Deskcheck was built in the open as a public-benefit project. If you
run it on your desk and something breaks — or a source you need does
not parse, or a verdict reads wrong — that report is the most valuable
thing you can give back. Write to the maintainers at
agent.embassy@proton.me with the claim, the card, and what you
expected. Reports from real desks shape what gets fixed first.

## License

MIT. See `LICENSE`. Take it, use it, fork it, give it away.
