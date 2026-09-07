# Xpens — Full App Analysis & Scrum Workflow Plan

- **App:** Xpens (expense tracker, personal productivity)
- **Design source:** `doc/prototype-b-dark.html` (dark premium web app, 5 pages, approved direction)
- **Date:** 2026-09-07 · **Status:** DRAFT for review
- **Currency:** EGP · **Target:** desktop-first responsive web app

---

## PART 1 — APP ANALYSIS

### 1. Vision & users

Xpens answers one question in under 5 seconds: *where did my money go?*
Primary user: a single individual (Seif, admin) tracking personal spending in EGP;
multi-user support exists so family members can have isolated data, not for social features.

**Goals:** (a) capture an expense in <5s, (b) always know budget-left per category,
(c) month-over-month insight without manual spreadsheets.
**Non-goals (v1):** bank sync, receipt OCR, mobile native apps, multi-currency,
sharing/social, recurring auto-posting (deferred to v1.1).

### 2. Prototype inventory (what the dark design proves)

| Page | Key components | State covered |
|---|---|---|
| Dashboard | Hero total + budget track, hstats, weekly bar chart (values, avg line, peak glow, today ring), category donut + legend, recent-expenses table, budget bars | Normal data |
| Expenses | Search + category filter (live), full table (description/category/date/payment/amount), empty-filter state | Normal + empty-filter |
| Budgets | 4 budget cards (spent/limit, bar, remaining, Edit) | Normal + near-limit warn |
| Insights | 6-month bars, budget-pressure bars, tip callout | Normal |
| Settings | Profile form, preferences (currency, month start), JSON export (working download) + import validation | Normal |
| Global | Sidebar nav (5 items), topbar (search-Enter, month picker, Add button), add-expense modal (chips, validation), `N` shortcut, Esc close, toasts via alert (placeholder) | — |

Missing from prototype (must be designed in build): login/signup screens, empty-first-run
state (zero expenses), error states (failed save, bad import), delete confirmations,
pagination beyond ~50 rows, admin user-management screen.

### 3. Functional requirements

- **FR-1 Auth & scoping:** local signup/login/logout; roles admin/user; every query
  scoped to `request.user` (per-user data isolation, no cross-user reads by ID manipulation).
- **FR-2 Expenses:** CRUD with amount (>0), date (default today), category (FK),
  note, payment method (cash/card/transfer); list newest-first; text search;
  category filter; add from any page via modal.
- **FR-3 Categories:** user-owneddefaults seeded (Food, Transport, Housing, Fun, Other)
  with color + icon; rename/add/deactivate (no hard delete while expenses reference).
- **FR-4 Budgets:** one monthly limit per category; used = sum of month's expenses;
  remaining + % bar; warn style at ≥90%; month boundary follows "month starts on" setting.
- **FR-5 Dashboard:** month total, budget-left, daily average, vs-last-month %;
  weekly bars; category donut; 5 latest transactions.
- **FR-6 Insights:** last-6-month totals; per-category % of budget; one tip callout
  (worst-pressure category ≥90%).
- **FR-7 Data portability:** export all user data as JSON (exact shape prototyped);
  import JSON with validation report (valid rows / rejected rows, nothing half-imported).
- **FR-8 Settings/Admin:** profile edit; currency display; month-start setting;
  admin: list/deactivate users (no data peek across users).

### 4. Non-functional requirements

- Desktop-first responsive (sidebar → icon rail ≤860px, grids stack ≤1100px).
- Every write validates server-side (prototype validation is cosmetic).
- Page loads feel instant on local network (<300ms server render, no heavy JS framework).
- Single deployable unit; SQLite-optional dev, PostgreSQL prod (matches original ET scope).

### 5. Recommended stack

Django 5 + PostgreSQL, server-rendered templates, zero frontend build step.
Charts stay CSS/SVG (as prototyped — no chart lib needed). Rationale: solo builder,
fastest path from prototype to production, admin panel free, auth/permissions built in.

### 6. Data model

```
User (django auth) 1──* Category (name, icon, color, active, owner)
User 1──* Expense (amount, date, note, payment, owner, category FK)
User 1──* Budget (category FK, month, limit)   [unique: owner+category+month]
User 1──* Profile (currency, month_start_day)
```

---

## PART 2 — SCRUM WORKFLOW

- **Cadence:** 1-week sprints, solo capacity **~12 story points/sprint**.
- **Point scale:** 1 (≈2h), 2 (≈4h), 3 (≈1d), 5 (≈2d), 8 (≈3–4d, must split if bigger).
- **Relations legend:** `→ blocks`, `← blocked by`, `~ relates to`.

### Releases

| Release | Goal | Epics | Exit criteria |
|---|---|---|---|
| **R1 v0.1 Foundation** (S1–S2) | Log in, own data, add expenses | EPIC-1, EPIC-2 | Auth works, CRUD + tests green, seeded categories |
| **R2 v0.2 Control** (S3–S4) | Budgets + dashboard live | EPIC-3, EPIC-4a | Budget bars + KPIs render from real data |
| **R3 v0.3 Insight** (S5) | Trends + data portability | EPIC-4b, EPIC-5 | Insights page + JSON round-trip verified |
| **R4 v1.0 Ship** (S6) | Hardened, releasable | EPIC-6 | DoD incl. deploy + backup note, demo clean |

### Epics

| Epic | Title | Description |
|---|---|---|
| EPIC-1 | Foundation & Auth | Project scaffold, Postgres, local auth + roles, per-user scoping on every query, login/signup pages |
| EPIC-2 | Expense management | Category + Expense models, CRUD + modal, search/filter, fast-capture flow |
| EPIC-3 | Budgets | Monthly limits, used/remaining computation, progress + warn states, Edit flow |
| EPIC-4 | Dashboard & Insights | KPIs, weekly chart, donut, 6-month trends, tip callout |
| EPIC-5 | Data portability | JSON export (prototyped shape), validated import with report |
| EPIC-6 | Settings, Admin & Ship | Profile/preferences, admin user mgmt, empty/error states, tests, deploy |

### Sprint 1 — Scaffold & Auth (R1 · EPIC-1 · 12 pts)

| ID | Type | Title (pts) | Description | Acceptance criteria | Relations |
|---|---|---|---|---|---|
| US-01 | Story (5) | Project scaffold + Postgres | New Django project, Postgres config, dev/prod settings split, repo README run steps | `runserver` boots on Postgres; README reproduces setup | → blocks US-02, US-03 |
| US-02 | Story (5) | Local auth + roles | Signup/login/logout with Django auth; `admin` vs `user` groups; login + signup pages in dark theme | Wrong password rejected; new signup lands as `user`; auth required everywhere | ← US-01; → blocks US-04 ~ US-06 |
| US-03 | Task (2) | Per-user scoping helper | Queryset mixin/`for_user()` + test proving user A cannot read user B rows by ID | Test: cross-user GET returns 404, not data | ← US-01; → blocks US-05 |

### Sprint 2 — Expenses core (R1 · EPIC-1/2 · 12 pts)

| ID | Type | Title (pts) | Description | Acceptance criteria | Relations |
|---|---|---|---|---|---|
| US-04 | Story (3) | Category + Expense models | Models per §6, seed 5 default categories per new user, admin registered | Migration clean; new user auto-gets 5 categories | ← US-02; → blocks US-05, US-07 |
| US-05 | Story (5) | Expense CRUD + modal | Add (modal, chips, amount>0 validation server-side), edit, delete with confirm; scoped to owner | Invalid amount rejected 400-side; delete asks confirm; all scoped | ← US-03, US-04; → blocks US-06 |
| US-06 | Story (3) | Expenses page: search + filter | Live text search + category dropdown + payment column, newest-first, empty-filter state | Typing filters; empty result shows friendly state | ← US-05; ~ US-09 (shares table CSS) |
| US-07 | Task (1) | Seed demo data command | `seed_demo` creates 1 month of realistic EGP data for screenshots/demos | Command documented; data matches prototype figures | ← US-04 |

### Sprint 3 — Budgets (R2 · EPIC-3 · 11 pts)

| ID | Type | Title (pts) | Description | Acceptance criteria | Relations |
|---|---|---|---|---|---|
| US-08 | Story (3) | Budget model + monthly rollover | `(owner, category, month)` limit; auto-create current-month rows from previous limits | New month inherits limits; unique constraint tested | ← US-04; → blocks US-09 |
| US-09 | Story (5) | Budgets page + dashboard bars | Cards with spent/limit, % bar, warn ≥90%, remaining label; same bars on dashboard | 95% food bar renders warn style from real data | ← US-08, US-05; ~ US-06 |
| US-10 | Story (3) | Edit budget flow | Modal/dialog to change a category limit; re-renders bars; validates limit ≥ 0 | Limit saved + bars update; negative rejected | ← US-09 |

### Sprint 4 — Dashboard (R2 · EPIC-4a · 12 pts)

| ID | Type | Title (pts) | Description | Acceptance criteria | Relations |
|---|---|---|---|---|---|
| US-11 | Story (3) | KPI hero (total/left/avg/%) | Month total, budget-left, daily avg, vs-last-month %; hero progress track; respects month-start setting | Figures match manual calc on demo data | ← US-09; → blocks US-14 |
| US-12 | Story (5) | Weekly chart + donut | Real-data bars with values, avg dashed line, peak glow, today ring; donut from category sums | Matches prototype visuals with real numbers | ← US-05; ~ US-13 |
| US-13 | Story (2) | Recent-expenses + `N` shortcut | 5-latest table; `View all→` routes to Expenses; `N` opens modal, Esc closes (already prototyped, wire to backend) | Shortcut works outside inputs | ← US-05 |
| US-14 | Task (2) | Month picker + topbar search | Picker switches month context; Enter in search jumps to Expenses filtered | Switching month requeries all cards | ← US-11 |

### Sprint 5 — Insights + portability (R3 · EPIC-4b/5 · 12 pts)

| ID | Type | Title (pts) | Description | Acceptance criteria | Relations |
|---|---|---|---|---|---|
| US-15 | Story (3) | Insights page | 6-month bars, budget-pressure bars, auto tip for worst ≥90% category | Tip names Food at 95% on demo data | ← US-09, US-11 |
| US-16 | Story (5) | JSON export | Download endpoint producing the prototyped shape (all user rows, no other users' data) | File imports cleanly (see US-17); only own rows present | ← US-05; → blocks US-17 |
| US-17 | Story (3) | JSON import + report | Upload, validate all-or-report: N imported / M rejected with reasons; never half-imports | Bad file → clear error, zero rows written | ← US-16 |
| US-18 | Task (1) | CSV export (bonus) | Same data as CSV for spreadsheets; drops to next sprint if S5 overflows | Opens correctly in Excel | ~ US-16 |

### Sprint 6 — Settings, admin & ship (R4 · EPIC-6 · 11 pts)

| ID | Type | Title (pts) | Description | Acceptance criteria | Relations |
|---|---|---|---|---|---|
| US-19 | Story (3) | Profile + preferences | Name/email/role edit; currency display; month-start day drives all month math | Changing start-day requeries dashboard correctly | ← US-11, US-08 |
| US-20 | Story (2) | Admin user management | Admin lists/deactivates users; deactivated cannot log in; no cross-user data view | Deactivated login rejected | ← US-02 |
| US-21 | Story (3) | Empty + error states | First-run empty dashboard, failed-save message, bad-import message, 404 page in theme | Each state screenshotted in PR | ← US-05, US-17 |
| US-22 | Task (3) | Test pass + deploy + docs | Full test run green, deploy notes, backup/restore note, README demo script | Clean clone → demo in <15 min | ← everything (ship gate) |

**Totals:** 22 items, 71 pts ≈ 6 solo sprints. Critical path: US-01 → US-02 → US-04 →
US-05 → US-08 → US-09 → US-11 → US-22.

### Definition of Done (every story)

Scoped queries + server-side validation; happy + invalid-input tests; dark-theme UI
matching prototype; no cross-user leak test where applicable; README/docs touched if
behavior changed.

### Top risks

1. Month-boundary math (month-start setting) — covered by US-19 tests, not assumed.
2. Import data corruption — mitigated by all-or-report rule in US-17.
3. Scope creep into OCR/bank-sync — explicitly v1.1, say no in review.

---

## TRACEABILITY (prototype → requirement → epic)

Hero/KPIs → FR-5 → EPIC-4 · Weekly chart/donut → FR-5 → EPIC-4 · Expenses table +
filters → FR-2 → EPIC-2 · Budget cards/bars → FR-4 → EPIC-3 · Insights →
FR-6 → EPIC-4 · Export/import → FR-7 → EPIC-5 · Profile/prefs → FR-8 → EPIC-6 ·
Auth pages (missing) → FR-1 → EPIC-1 · Admin screen (missing) → FR-8 → EPIC-6.
