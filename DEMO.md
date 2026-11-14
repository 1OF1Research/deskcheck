# DEMO — Deskcheck, run live 2026-11-14 (America/Chicago)

Environment: this machine, Python 3.12.3, network fetch of public sources.
Clean-checkout copy (/tmp/deskcheck-clean) reproduced every result below:
tests ALL PASS, demo verdicts identical, verify PASS.

```
CAPTURED  NWS alerts — Rutherford County TN: 242 bytes, sha256 1b454599420da507…
CAPTURED  NWS forecast — Murfreesboro TN: 13157 bytes, sha256 eaa28495f654eb15…
CAPTURED  FAA NAS status: 1008 bytes, sha256 f73dfef2f3da70c3…
Store: /home/hatch/workspace/office-omega/mozilla-banger/deskcheck/live-store  (3 captures on record)

====================================================================
CLAIM: The low tonight will be around 27 degrees.
VERDICT: SUPPORTED
WHY: Captured source text states the claim, including every number in it.

  SOURCE: NWS forecast — Murfreesboro TN (https://api.weather.gov/gridpoints/OHX/65,44/forecast)
  CAPTURED: 2026-11-14T23:19:25+00:00  FRESHNESS: fresh
  IT SAYS: "Clear, with a low around 27."
  CAPTURE DIGEST: eaa28495f654eb15a389d00c…
====================================================================
====================================================================
CLAIM: The low tonight will be around 42 degrees.
VERDICT: CONTRADICTED ON THE NUMBERS
WHY: Captured sources cover this claim's subject but state different numbers. The passages below are what the record actually says.

  SOURCE: NWS forecast — Murfreesboro TN (https://api.weather.gov/gridpoints/OHX/65,44/forecast)
  CAPTURED: 2026-11-14T23:19:25+00:00  FRESHNESS: fresh
  IT SAYS: "Clear, with a low around 27."
  CAPTURE DIGEST: eaa28495f654eb15a389d00c…

  SOURCE: NWS forecast — Murfreesboro TN (https://api.weather.gov/gridpoints/OHX/65,44/forecast)
  CAPTURED: 2026-11-14T23:19:25+00:00  FRESHNESS: fresh
  IT SAYS: "Mostly clear, with a low around 28."
  CAPTURE DIGEST: eaa28495f654eb15a389d00c…

  SOURCE: NWS forecast — Murfreesboro TN (https://api.weather.gov/gridpoints/OHX/65,44/forecast)
  CAPTURED: 2026-11-14T23:19:25+00:00  FRESHNESS: fresh
  IT SAYS: "Clear, with a low around 28."
  CAPTURE DIGEST: eaa28495f654eb15a389d00c…

  SOURCE: NWS forecast — Murfreesboro TN (https://api.weather.gov/gridpoints/OHX/65,44/forecast)
  CAPTURED: 2026-11-14T23:19:25+00:00  FRESHNESS: fresh
  IT SAYS: "Tuesday Night Clear, with a low around 29."
  CAPTURE DIGEST: eaa28495f654eb15a389d00c…
====================================================================
====================================================================
CLAIM: A tornado warning is in effect for Rutherford County.
VERDICT: NOT IN THE RECORD
WHY: The record touches this claim's words only in passing (a heading, a place name) and nowhere states the claim itself. The record cannot carry it.

  NO PASSAGES — the record does not speak to this claim.
====================================================================

##### Shipped public-record example #####
SEEDED  Secretary of Transportation statement — ground stop cause, Nov 14 2026: 391 bytes (Summary of the on-record public statement of the U.S. Secret…)
SEEDED  FAA advisory — nationwide ground stop, Nov 13 2026: 321 bytes (Text of the FAA Command Center advisory of Friday, November …)

--- Check 1: a claim the record refuses to carry as fact ---
====================================================================
CLAIM: The FAA has determined that a faulty router caused the November 13 ground stop.
VERDICT: NOT YET KNOWN
WHY: The captured record, on this very point, says the matter is not settled. Do not print the claim as fact; the card shows what the record does say.

  SOURCE: Secretary of Transportation statement — ground stop cause, Nov 14 2026 (On-record public statement, broadcast 2026-11-14; summary retrieved 2026-11-14)
  CAPTURED: 2026-11-14T19:00:00+00:00  FRESHNESS: archival
  IT SAYS: "The cause of the November 13 ground stop is still being worked out, and no verdict has been reached."
  CAPTURE DIGEST: 5f59c95d6787a8d1248e2199…

  SOURCE: Secretary of Transportation statement — ground stop cause, Nov 14 2026 (On-record public statement, broadcast 2026-11-14; summary retrieved 2026-11-14)
  CAPTURED: 2026-11-14T19:00:00+00:00  FRESHNESS: archival
  IT SAYS: "Two candidate causes have been named: installer error by the contractor L3 Harris, or a faulty router that L3 Harris was swapping in during the copper-to-fiber change, which started flooding the other routers in the system."
  CAPTURE DIGEST: 5f59c95d6787a8d1248e2199…
====================================================================

--- Check 2: a claim the record does carry ---
====================================================================
CLAIM: All departing flights were ground stopped until further notice.
VERDICT: SUPPORTED
WHY: Captured source text states the substance of the claim, in the passages below.

  SOURCE: FAA advisory — nationwide ground stop, Nov 13 2026 (FAA Command Center advisory, republished in contemporaneous reporting (northjersey.com), retrieved 2026-11-14)
  CAPTURED: 2026-11-14T18:00:00+00:00  FRESHNESS: archival
  IT SAYS: "All departing traffic should remain ground stopped until further notice."
  CAPTURE DIGEST: f3b4bdb936dac5d3ce58e464…
====================================================================

--- Timeline: the cause of the November 13 ground stop ---
TIMELINE for: cause ground stop

— Secretary of Transportation statement — ground stop cause, Nov 14 2026 · captured 2026-11-14T19:00:00+00:00 · seeded-public-record
    "The cause of the November 13 ground stop is still being worked out, and no verdict has been reached."
    STATUS AT THIS MOMENT: stated as NOT YET KNOWN.

PASS  NWS alerts — Rutherford County TN (2026-11-14T23:19:19+00:00): digest matches
PASS  NWS forecast — Murfreesboro TN (2026-11-14T23:19:25+00:00): digest matches
PASS  FAA NAS status (2026-11-14T23:19:31+00:00): digest matches
RESULT: PASS — the record is intact

PASS  Secretary of Transportation statement — ground stop cause, Nov 14 2026 (2026-11-14T19:00:00+00:00): digest matches
PASS  FAA advisory — nationwide ground stop, Nov 13 2026 (2026-11-14T18:00:00+00:00): digest matches
RESULT: PASS — the record is intact

```
