#!/usr/bin/env python3
"""Deskcheck — check an official claim before you repeat it.

A free, local-first desk tool for small newsrooms and public information
desks. It captures official public sources (raw bytes + SHA-256 digest +
retrieval time), checks a claim against the captured record, and prints a
claim card: the verdict the record actually supports, the exact source
words, when the source spoke, when it was captured, how fresh it is, and
an explicit line for what is not yet known.

Pure Python standard library. No accounts, no cloud, no model, no cost.
All evidence lives in a folder on your own machine.

Commands:
  capture   fetch every source in sources.json into the evidence store
  check     check one claim against the captured record -> a claim card
  timeline  show how the record on a topic changed across captures
  verify    re-verify a store (digests, verbatim passages, freshness)
  demo      run the shipped public-record example end to end

Run `python3 deskcheck.py <command> --help` for options.
"""
import argparse, hashlib, json, re, sys, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

USER_AGENT = "Deskcheck/1.0 (public-benefit desk tool; stdlib fetch)"
UNDETERMINED_MARKERS = [
    "undetermined", "not yet determined", "has not been determined",
    "no verdict", "still being worked out", "still under investigation",
    "cause is unknown", "not yet known", "remains unknown",
]
STOPWORDS = set("""the a an of to in on for and or is are was were be been it its
this that with as at by from has have had not no yes all any can could will
would should may might do does did so if but about into over under after
before between during their there here which who whom what when where why
how one two three per via etc""".split())
DAY_WORDS = {"today", "tonight", "tomorrow", "monday", "tuesday",
             "wednesday", "thursday", "friday", "saturday", "sunday"}
NEG_WORDS = {"no", "not", "never", "none", "cannot", "can't", "won't",
             "isn't", "aren't", "wasn't", "weren't", "don't", "doesn't",
             "didn't", "couldn't", "shouldn't", "wouldn't"}


class StoreError(Exception):
    """The store or a config file cannot be read; said plainly."""


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso(s):
    dt = datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def word_tokens(text):
    toks = re.findall(r"[a-z][a-z'-]*", text.lower())
    return {t[:-2] if t.endswith("'s") else t for t in toks}


def day_anchors_of(text):
    return word_tokens(text) & DAY_WORDS


def has_negation(text):
    return bool(word_tokens(text) & NEG_WORDS)


def norm_num(s):
    s = s.replace(",", "")
    try:
        f = float(s)
    except ValueError:
        return s
    return str(int(f)) if f == int(f) else str(f)


def claim_numbers(claim):
    """The claim's numbers, each with its context: the significant
    words around it, which a supporting sentence must share before the
    number counts as bound to the claim's subject."""
    words = [(m.group(0), m.start(), m.end())
             for m in re.finditer(r"[A-Za-z][A-Za-z'-]+", claim)]

    def clean(ws):
        res = []
        for w in ws:
            t = w.lower()
            if t.endswith("'s"):
                t = t[:-2]
            if t not in STOPWORDS and len(t) > 2:
                res.append(t)
        return res

    out = []
    pat = (r"\d+(?:[.,]\d+)?\s?(?:%|percent|°[FC]|degrees|mph|am|pm|"
           r"AM|PM)?")
    for m in re.finditer(pat, claim):
        raw = re.sub(r"[^\d.,]", "", m.group(0))
        # Context stops at clause boundaries (a comma, a semicolon, or
        # the word "and"): a number's subject lives in its own clause,
        # so the second half of a joint claim cannot borrow the first
        # half's words to bind its number.
        seg_start = 0
        head = claim[:m.start()].lower()
        for b in (",", ";", " and "):
            i = head.rfind(b)
            if i >= 0:
                seg_start = max(seg_start, i + len(b))
        seg_end = len(claim)
        tail = claim[m.end():].lower()
        for b in (",", ";", " and "):
            i = tail.find(b)
            if i >= 0:
                seg_end = min(seg_end, m.end() + i)
        before = clean([w for w, s, e in words
                        if e <= m.start() and s >= seg_start])[-3:]
        after = clean([w for w, s, e in words
                       if s >= m.end() and e <= seg_end])[:1]
        out.append({"raw": raw, "norm": norm_num(raw),
                    "context": set(before) | set(after)})
    return [n for n in out if n["norm"]]


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------- store

def load_manifest(store):
    p = Path(store) / "manifest.json"
    if p.exists():
        try:
            data = json.loads(p.read_text())
        except Exception as e:
            raise StoreError(
                f"the store's manifest at {p} cannot be read "
                f"({type(e).__name__}). The record cannot be trusted "
                f"until the store is rebuilt or re-captured.")
        if not isinstance(data, dict) or \
                not isinstance(data.get("captures"), list):
            raise StoreError(
                f"the store's manifest at {p} is not in the expected "
                f"shape. The record cannot be trusted until the store "
                f"is rebuilt.")
        return data
    return {"captures": []}


def save_manifest(store, manifest):
    p = Path(store) / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2))
    tmp.replace(p)


def evidence_text(raw, content_hint=""):
    """Extract human-readable text from captured bytes (JSON/XML/HTML/text)."""
    text = raw.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            data = json.loads(text)
            chunks = []
            def walk(o, inside=False):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k in ("headline", "description", "instruction",
                                 "name", "detailedForecast", "title",
                                 "event", "senderName", "areaDesc"):
                            if isinstance(v, str):
                                chunks.append(v)
                            elif isinstance(v, (int, float)):
                                chunks.append(str(v))
                            else:
                                walk(v, inside=True)
                        else:
                            walk(v, inside)
                elif isinstance(o, list):
                    for v in o:
                        walk(v, inside)
                elif inside and isinstance(o, str):
                    chunks.append(o)
            walk(data)
            if chunks:
                return "\n".join(chunks)
        except Exception:
            pass
    if "<" in text[:2000]:
        text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [p.strip() for p in parts
            if len(p.strip()) > 8 or any(ch.isdigit() for ch in p)]


# ---------------------------------------------------------------- capture

def cmd_capture(args):
    try:
        cfg = json.loads(Path(args.sources).read_text())
    except Exception as e:
        raise StoreError(
            f"the sources file {args.sources} cannot be read "
            f"({type(e).__name__}). Fix it and run capture again; "
            f"nothing was captured.")
    if not isinstance(cfg, dict) or \
            not isinstance(cfg.get("sources"), list):
        raise StoreError(
            f"the sources file {args.sources} has no 'sources' list. "
            f"Nothing was captured.")
    for i, src in enumerate(cfg["sources"]):
        if not isinstance(src, dict) or not src.get("url") \
                or not src.get("name"):
            raise StoreError(
                f"source #{i + 1} in {args.sources} is missing its "
                f"'name' or 'url'. Nothing was captured.")
    store = Path(args.store)
    (store / "evidence").mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(store)
    ok_count = 0
    for src in cfg["sources"]:
        name = src["name"]
        try:
            req = urllib.request.Request(src["url"],
                                         headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
        except Exception as e:
            print(f"CAPTURE FAILED  {name}: {type(e).__name__} — no bytes stored; "
                  f"the record will say this source is unavailable, never guess.")
            manifest["captures"].append({
                "id": f"failed-{name}-{now_iso()}", "source": name,
                "url": src["url"], "retrieved_at": now_iso(),
                "method": "live-fetch", "status": "unavailable",
                "error": type(e).__name__})
            continue
        cid = f"{name}-{sha256_hex(raw)[:12]}"
        (store / "evidence" / f"{cid}.bin").write_bytes(raw)
        entry = {
            "id": cid, "source": name, "url": src["url"],
            "retrieved_at": now_iso(), "method": "live-fetch",
            "status": "ok", "sha256": sha256_hex(raw), "bytes": len(raw),
            "freshness_window_minutes": src.get("freshness_window_minutes"),
            "provenance": src.get("provenance", "Live fetch of the public source.")}
        manifest["captures"] = [c for c in manifest["captures"]
                                 if c["id"] != cid]
        manifest["captures"].append(entry)
        ok_count += 1
        print(f"CAPTURED  {name}: {len(raw)} bytes, sha256 {entry['sha256'][:16]}…")
    save_manifest(store, manifest)
    print(f"Store: {store}  ({len(manifest['captures'])} captures on record)")
    if not ok_count:
        print("NO SOURCE COULD BE CAPTURED — the store holds no new "
              "evidence from this run.")
    return 0 if ok_count else 1


# ---------------------------------------------------------------- check

def anchors(claim):
    """Checkable anchors in a claim: numbers, and significant terms."""
    nums = re.findall(r"\d+(?:[.,]\d+)?\s?(?:%|percent|°[FC]|degrees|mph|am|pm|AM|PM)?",
                      claim)
    words = re.findall(r"[A-Za-z][A-Za-z'-]+", claim.lower())
    terms = [w for w in words if w not in STOPWORDS and len(w) > 2]
    caps = re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)*\b", claim)
    return {"numbers": [n.strip() for n in nums if n.strip()],
            "terms": terms, "phrases": caps}


def freshness_of(cap, at):
    if cap.get("status") != "ok":
        return "unavailable"
    window = cap.get("freshness_window_minutes")
    if window is None:
        return "archival"
    try:
        then = parse_iso(cap["retrieved_at"])
    except Exception:
        return "stale"  # an unreadable capture time proves nothing fresh
    age = (at - then).total_seconds() / 60.0
    return "fresh" if age <= window else "stale"


def check_claim(store, claim, at=None):
    at = at or datetime.now(timezone.utc)
    manifest = load_manifest(store)
    a = anchors(claim)
    nums = claim_numbers(claim)
    claim_days = day_anchors_of(claim)
    claim_neg = has_negation(claim)
    card = {"claim": claim, "checked_at": at.isoformat(timespec="seconds"),
            "anchors": a, "matches": [], "verdict": None, "not_known": []}
    ok_caps = [c for c in manifest["captures"] if c.get("status") == "ok"]
    if not ok_caps:
        card["verdict"] = "NO RECORD"
        card["reason"] = ("The evidence store holds no successful captures. "
                           "Capture the sources first; a check without a "
                           "record would be a guess.")
        return card
    scored = []
    for cap in ok_caps:
        cid, want = cap.get("id"), cap.get("sha256")
        if not cid or not want:
            card["verdict"] = "RECORD BROKEN"
            card["reason"] = ("A capture in the manifest is missing its "
                              "identity or its digest. The record itself "
                              "cannot be trusted; rebuild the store.")
            return card
        try:
            raw = (Path(store) / "evidence" / f"{cid}.bin").read_bytes()
        except OSError:
            card["verdict"] = "RECORD BROKEN"
            card["reason"] = (f"Capture {cid} is on record but its "
                              f"evidence file is missing. The record "
                              f"itself cannot be trusted; re-capture "
                              f"the source.")
            return card
        if sha256_hex(raw) != want:
            card["verdict"] = "RECORD BROKEN"
            card["reason"] = (f"Capture {cid} no longer matches its "
                              f"recorded digest. The record itself cannot "
                              f"be trusted; re-capture the source.")
            return card
        text = evidence_text(raw)
        for s in sentences(text):
            low = s.lower()
            shared = [t for t in a["terms"]
                      if re.search(rf"\b{re.escape(t)}\b", low)]
            if len(shared) >= 2:
                sdays = day_anchors_of(s)
                scored.append({
                    "capture": cap, "sentence": s, "shared_terms": shared,
                    "sentence_numbers": [norm_num(n) for n in
                                         re.findall(r"\d+(?:[.,]\d+)?", s)],
                    "freshness": freshness_of(cap, at),
                    "day_ok": (not claim_days or not sdays
                               or bool(claim_days & sdays)),
                    "neg": has_negation(s), "terms_set": word_tokens(s)})
    def as_match(m):
        return {"source": m["capture"]["source"],
                "source_url": m["capture"]["url"],
                "passage": m["sentence"],
                "captured_at": m["capture"]["retrieved_at"],
                "capture_sha256": m["capture"]["sha256"],
                "freshness": m["freshness"]}

    def fresh_first(entries):
        """Passages a verdict rests on: never show a stale passage when
        a fresh or archival one carries the same verdict."""
        nf = [m for m in entries if m["freshness"] != "stale"]
        return [as_match(x) for x in (nf if nf else entries)]

    topic = [m for m in scored if len(m["shared_terms"]) >= 2]
    strong = [m for m in scored
              if len(m["shared_terms"]) >= 3
              or (len(m["shared_terms"]) >= 2
                  and any(n["norm"] in m["sentence_numbers"] for n in nums))]
    # NOT YET KNOWN: the record itself says the matter is undetermined.
    for m in topic:
        low = m["sentence"].lower()
        if any(mk in low for mk in UNDETERMINED_MARKERS):
            card["matches"] = [as_match(x) for x in topic]
            card["verdict"] = "NOT YET KNOWN"
            card["reason"] = ("The captured record, on this very point, says "
                               "the matter is not settled. Do not print the "
                               "claim as fact; the card shows what the "
                               "record does say.")
            card["not_known"].append(m["sentence"])
            return card
    # STALE: judged on the captures this verdict would rest on — the
    # ones speaking to the claim — never on the whole store.
    windowed = [m for m in topic if m["freshness"] in ("fresh", "stale")]
    if topic and windowed and all(m["freshness"] == "stale"
                                  for m in windowed):
        card["matches"] = [as_match(x) for x in topic]
        card["verdict"] = "SOURCE STALE — REFUSED"
        card["reason"] = ("Every capture that speaks to this claim is "
                           "older than its freshness window. Re-capture "
                           "before relying on this check.")
        return card
    if not topic:
        card["verdict"] = "NOT IN THE RECORD"
        card["reason"] = ("No captured source speaks to this claim. That "
                           "is not proof the claim is false — it means the "
                           "record on this desk cannot carry it. Capture "
                           "the source that would know, then check again.")
        return card
    if nums:
        compat = [m for m in topic if m["day_ok"]]

        def bound(n):
            return any(n["norm"] in m["sentence_numbers"]
                       and (not n["context"]
                            or n["context"] & m["terms_set"])
                       for m in compat)

        def conflict(n):
            return any(len(m["shared_terms"]) >= 2
                       and (n["context"] & m["terms_set"])
                       and any(x != n["norm"]
                               for x in m["sentence_numbers"])
                       for m in compat)

        def present(n):
            return any(n["norm"] in m["sentence_numbers"] for m in compat)

        def hits():
            return [m for m in compat
                    if any(n["norm"] in m["sentence_numbers"] for n in nums)]

        if all(bound(n) for n in nums):
            card["matches"] = fresh_first(hits() or compat)
            card["verdict"] = "SUPPORTED"
            card["reason"] = ("Captured source text states the claim, "
                               "including every number in it.")
        elif any(conflict(n) for n in nums):
            card["matches"] = [as_match(x) for x in compat or topic]
            card["verdict"] = "CONTRADICTED ON THE NUMBERS"
            card["reason"] = ("Captured sources cover this claim's subject "
                               "but state different numbers. The passages "
                               "below are what the record actually says.")
        elif all(present(n) for n in nums):
            card["matches"] = fresh_first(hits() or compat)
            card["verdict"] = "SUPPORTED"
            card["reason"] = ("Captured source text states the claim, "
                               "including every number in it.")
        elif any(m["sentence_numbers"] for m in compat):
            card["matches"] = [as_match(x) for x in compat]
            card["verdict"] = "CONTRADICTED ON THE NUMBERS"
            card["reason"] = ("Captured sources cover this claim's subject "
                               "but state different numbers. The passages "
                               "below are what the record actually says.")
        elif any(m["sentence_numbers"] for m in topic):
            card["verdict"] = "NOT IN THE RECORD"
            card["reason"] = ("The record states figures for a different "
                               "moment than the claim names. It cannot "
                               "carry the claim as stated; check the "
                               "record for the claim's own moment.")
        else:
            card["verdict"] = "NOT IN THE RECORD"
            card["reason"] = ("Sources touch this claim's subject but "
                               "state no numbers at all; the record cannot "
                               "carry a numbered claim. Check the source "
                               "that publishes the figure.")
        return card
    support = [m for m in strong
               if m["day_ok"] and m["neg"] == claim_neg]
    if support:
        card["matches"] = fresh_first(support)
        card["verdict"] = "SUPPORTED"
        card["reason"] = ("Captured source text states the substance of "
                           "the claim, in the passages below.")
        return card
    if strong and any(m["neg"] != claim_neg for m in strong):
        card["verdict"] = "NOT IN THE RECORD"
        card["reason"] = ("The record speaks to this claim only in the "
                           "negative — it states the opposite of the "
                           "claim as written. The record cannot carry it.")
        return card
    if strong:
        card["verdict"] = "NOT IN THE RECORD"
        card["reason"] = ("The record states this for a different moment "
                           "than the claim names. It cannot carry the "
                           "claim as stated.")
        return card
    card["verdict"] = "NOT IN THE RECORD"
    card["reason"] = ("The record touches this claim's words only in "
                       "passing (a heading, a place name) and nowhere "
                       "states the claim itself. The record cannot "
                       "carry it.")
    return card


def print_card(card):
    print("=" * 68)
    print(f"CLAIM: {card['claim']}")
    print(f"VERDICT: {card['verdict']}")
    print(f"WHY: {card['reason']}")
    for m in card["matches"][:4]:
        print(f"\n  SOURCE: {m['source']} ({m['source_url']})")
        print(f"  CAPTURED: {m['captured_at']}  FRESHNESS: {m['freshness']}")
        print(f"  IT SAYS: \"{m['passage']}\"")
        print(f"  CAPTURE DIGEST: {m['capture_sha256'][:24]}…")
    if not card["matches"]:
        print("\n  NO PASSAGES — the record does not speak to this claim.")
    print("=" * 68)


def cmd_check(args):
    card = check_claim(args.store, args.claim)
    print_card(card)
    out = Path(args.store) / "cards"
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    (out / f"{stamp}-card.json").write_text(json.dumps(card, indent=2))
    return 0


# ---------------------------------------------------------------- timeline

def cmd_timeline(args):
    manifest = load_manifest(args.store)
    terms = [t.lower() for t in args.terms]
    print(f"TIMELINE for: {' '.join(args.terms)}")
    found = False
    caps = sorted((c for c in manifest["captures"] if c.get("status") == "ok"),
                  key=lambda c: c["retrieved_at"])
    for cap in caps:
        try:
            raw = (Path(args.store) / "evidence"
                   / f"{cap['id']}.bin").read_bytes()
        except OSError:
            print(f"\n— {cap['source']} · RECORD BROKEN: its evidence "
                  f"file is missing; its passages are withheld.")
            found = True
            continue
        if sha256_hex(raw) != cap.get("sha256"):
            print(f"\n— {cap['source']} · RECORD BROKEN: this capture no "
                  f"longer matches its recorded digest; its passages "
                  f"are withheld.")
            found = True
            continue
        hits = [s for s in sentences(evidence_text(raw))
                if sum(1 for t in terms
                       if re.search(rf"\b{re.escape(t)}\b", s.lower()))
                >= min(2, len(terms))]
        if hits:
            found = True
            print(f"\n— {cap['source']} · captured {cap['retrieved_at']} "
                  f"· {cap.get('method')}")
            for h in hits[:3]:
                print(f"    \"{h}\"")
            if any(mk in " ".join(hits).lower() for mk in UNDETERMINED_MARKERS):
                print("    STATUS AT THIS MOMENT: stated as NOT YET KNOWN.")
    if not found:
        print("  The record holds nothing on this topic yet.")
    return 0


# ---------------------------------------------------------------- verify

def cmd_verify(args):
    store = Path(args.store)
    manifest = load_manifest(store)
    if not manifest["captures"]:
        print("RESULT: EMPTY — this store holds no captures; there is "
              "nothing to verify yet. Run capture first.")
        return 0
    bad = 0
    for cap in manifest["captures"]:
        if cap.get("status") != "ok":
            print(f"SKIP  {cap['source']}: capture was unavailable "
                  f"({cap.get('error')}) — recorded honestly, nothing to verify.")
            continue
        p = store / "evidence" / f"{cap['id']}.bin"
        if not p.exists():
            print(f"FAIL  {cap['id']}: evidence file missing.")
            bad += 1
            continue
        raw = p.read_bytes()
        ok = sha256_hex(raw) == cap["sha256"] and len(raw) == cap["bytes"]
        print(f"{'PASS' if ok else 'FAIL'}  {cap['source']} "
              f"({cap['retrieved_at']}): digest {'matches' if ok else 'MISMATCH'}"
              f" · freshness now: "
              f"{freshness_of(cap, datetime.now(timezone.utc))}")
        bad += 0 if ok else 1
    cards = sorted((store / "cards").glob("*-card.json")) \
        if (store / "cards").exists() else []
    for cf in cards:
        try:
            card = json.loads(cf.read_text())
        except Exception:
            print(f"FAIL  card {cf.name}: the card file cannot be read.")
            bad += 1
            continue
        for m in card["matches"]:
            cap = next((c for c in manifest["captures"]
                        if c["sha256"] == m["capture_sha256"]), None)
            if cap is None:
                print(f"FAIL  card {cf.name}: passage's capture not in manifest.")
                bad += 1
                continue
            raw = (store / "evidence" / f"{cap['id']}.bin").read_bytes()
            if m["passage"] not in sentences(evidence_text(raw)) and \
               m["passage"] not in evidence_text(raw):
                print(f"FAIL  card {cf.name}: passage not verbatim in capture.")
                bad += 1
    print(f"RESULT: {'PASS — the record is intact' if bad == 0 else f'FAIL — {bad} problem(s)'}")
    return 0 if bad == 0 else 1


# ---------------------------------------------------------------- demo

def seed_store(store, bundle_dir):
    """Load a folder of public-record text files into a store, honestly
    labelled as seeded public record (not a live fetch)."""
    store = Path(store)
    (store / "evidence").mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(store)
    for meta_file in sorted(Path(bundle_dir).glob("*.json")):
        meta = json.loads(meta_file.read_text())
        raw = (Path(bundle_dir) / meta["file"]).read_bytes()
        cid = f"{meta['source']}-{sha256_hex(raw)[:12]}"
        (store / "evidence" / f"{cid}.bin").write_bytes(raw)
        entry = {"id": cid, "source": meta["source"], "url": meta["url"],
                 "retrieved_at": meta["retrieved_at"],
                 "method": "seeded-public-record", "status": "ok",
                 "sha256": sha256_hex(raw), "bytes": len(raw),
                 "freshness_window_minutes": None,
                 "provenance": meta["provenance"]}
        manifest["captures"] = [c for c in manifest["captures"]
                                 if c["id"] != cid]
        manifest["captures"].append(entry)
        print(f"SEEDED  {meta['source']}: {len(raw)} bytes "
              f"({meta['provenance'][:60]}…)")
    save_manifest(store, manifest)


def cmd_demo(args):
    here = Path(__file__).parent
    store = Path(args.store)
    seed_store(store, here / "examples" / "faa-cause")
    print("\n--- Check 1: a claim the record refuses to carry as fact ---")
    print_card(check_claim(store,
        "The FAA has determined that a faulty router caused the "
        "November 13 ground stop."))
    print("\n--- Check 2: a claim the record does carry ---")
    print_card(check_claim(store,
        "All departing flights were ground stopped until further notice."))
    print("\n--- Timeline: the cause of the November 13 ground stop ---")
    class T: pass
    t = T(); t.store = str(store); t.terms = ["cause", "ground", "stop"]
    cmd_timeline(t)
    return 0


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(prog="deskcheck", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("capture"); p.add_argument("--store", default="store")
    p.add_argument("--sources", default="sources.json")
    p.set_defaults(fn=cmd_capture)
    p = sub.add_parser("check"); p.add_argument("--store", default="store")
    p.add_argument("claim"); p.set_defaults(fn=cmd_check)
    p = sub.add_parser("timeline"); p.add_argument("--store", default="store")
    p.add_argument("terms", nargs="+"); p.set_defaults(fn=cmd_timeline)
    p = sub.add_parser("verify"); p.add_argument("--store", default="store")
    p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("demo"); p.add_argument("--store", default="demo-store")
    p.set_defaults(fn=cmd_demo)
    args = ap.parse_args()
    try:
        return args.fn(args)
    except StoreError as e:
        print(f"DESKCHECK ERROR: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
