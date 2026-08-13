# Version

**Current version:** 1.0.0

**Release date:** 2026-08

**Release type:** MVP — implementation complete, Critical/High security and correctness findings
remediated, real-world integration testing not yet performed.

## Version History

| Version | Date | Summary |
|---|---|---|
| 1.0.0 | 2026-08 | First frozen release. Milestones 1–7 implemented. All 7 Critical and 6 High findings from `ARCHITECTURE_AUDIT.md` remediated (see `FIX_SUMMARY.md`). Full documentation set corrected and made internally consistent. |
| 0.x (unversioned) | 2026-06 | Original engineering pass across Milestones 1–7. Later found by `ARCHITECTURE_AUDIT.md` to contain 7 Critical and 6 High severity issues, including a Razorpay integration that could not function correctly for more than one tenant and a non-functional Reports/Exports feature. Not separately tagged; superseded by 1.0.0. |

## Versioning Scheme

Semantic-style (`MAJOR.MINOR.PATCH`), applied prospectively starting at this release. No prior
version was formally tagged (no `.git` history existed in the source repository provided for this
work — see `FINAL_RELEASE_REPORT.md` § Repository Statistics).

## Component Versions (as declared in dependency manifests)

- Backend: Python 3.11, FastAPI 0.110.1, motor 3.3.1, Pydantic ≥2.6.4
- Frontend: React 19, Create React App + CRACO
- Database: MongoDB 6.0+ (driver-compatible; no server-side version pin in this repository)
