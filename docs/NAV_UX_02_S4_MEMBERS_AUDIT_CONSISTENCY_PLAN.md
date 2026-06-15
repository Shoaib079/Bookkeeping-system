# NAV-UX-02-S4 — Members & Audit Log Cross-Surface Consistency: Decision Plan

**Mode:** Planning + **S4-IMPL-1 implemented (2026-06).** Mobile Members relocation complete; desktop, roles, routes, and render unchanged.

## 1. Current exposure map

| Page | route_key | render_fn | desktop placement | mobile placement | role_gate |
|---|---|---|---|---|---|
| Members | `NAV_MEMBERS` | `render_user_management` | accordion `settings` "Settings" (`app.py:3473`) | **People hub** (`_MOBILE_HUB_CONFIG["people"]`, `app.py:3409`) | **owner-only** (in owner list only; absent from manager/cashier/partner/viewer in `_NAV_ROLE_PAGES`) |
| Audit Log | `NAV_AUDIT_LOG` | `render_audit_log` | accordion `settings` "Settings" (`app.py:3475`) | **More → Admin** (`_MOBILE_HUB_CONFIG["more"]` admin section, `app.py:3418-3421`) | **owner + manager** (in owner *and* manager lists; absent from cashier/partner/viewer) |

Peer Settings pages for contrast — Company Settings, Permissions, Backup & Restore are **owner-only** (`app.py:3472,3474,3476`); on mobile Company Settings + Backup & Restore + Audit Log live under **More → Admin**.

**Two inconsistencies confirmed:**
1. **Members** is **Settings (admin) on desktop** but **People hub (operational) on mobile** — same page, two different domains.
2. **Audit Log** is **owner+manager** while the rest of the Settings/admin config pages are **owner-only** — a role outlier inside the Settings group (placement is consistent: Settings desktop / More→Admin mobile).

## 2. Purpose classification

| Page | Purpose | Domain |
|---|---|---|
| Members (`render_user_management`) | Manage **user accounts & memberships** — add/remove users, assign roles. This is **access administration** (who may use the system), not a business contact record. | **Admin / Settings** |
| Audit Log (`render_audit_log`) | **Read-only activity/event log** — security & compliance oversight. Grants **no mutating capability**. | **Admin / Settings (oversight)** |

Key distinction: the **People hub** holds **business people *records*** (Customers, Vendors, Receivables, Payables, Workers, Partner Accounts). **Members are *system users*, not business contacts** — conflating them in People mixes access-control with operational records.

## 3. Recommended ownership model

- **Members → Settings / Administration** (not People). It is access administration; its home is the Settings (admin) domain on **both** surfaces.
- **Audit Log → Settings / Administration (oversight)**. Already there on both surfaces; keep.
- **Principle A — Settings = admin domain = configuration + oversight:** Company Settings, Members, Permissions, Backup & Restore (configuration) **plus** Audit Log (oversight). Configuration pages are owner-only; oversight (Audit Log) is the **documented exception** that is also manager-visible.
- **Principle B — People hub = operational people *records* only:** Customers, Vendors, Receivables, Payables, Workers, Partner Accounts. **Members is removed** from the People hub (it is admin, not an operational record).

## 4. Role-gate recommendation

- **Members — keep owner-only.** Adding/removing users and changing roles is high-sensitivity access control; owner-only is correct. (A future explicit `manage_members` permission could widen it, but **no change now**.)
- **Audit Log — keep manager-visible (owner + manager).** It is **read-only** oversight and grants no mutation, so manager read access is low-risk and operationally useful for troubleshooting/oversight. **Answer to Q3: yes, remain manager-visible.** Optional future note: if any export/PII-sensitive field is added, gate that field (not the page) to owner.
- **Q4 — Settings is *not* strictly owner-only:** it is the **admin domain** holding owner-only configuration **and** one manager-visible oversight page (Audit Log). This exception is explicit and intentional, not a leak.

## 5. Mobile / Desktop consistency recommendation

- **Q2: Yes — mobile placement should match desktop ownership.** Move **Members** on mobile from the **People hub** → **More → Admin** (alongside Company Settings, Backup & Restore, Audit Log), matching its desktop Settings home.
- **Audit Log:** already consistent (Settings desktop / More→Admin mobile) — no move.
- **Q5: Yes — the People hub should contain operational people records only** (remove Members; keep Customers/Vendors/Receivables/Payables/Workers/Partners).
- Net mobile change in the implementation slice = **relocate one page (Members)**; everything else stays.

## 6. React route contract (freeze 1:1)

Admin domain under `/settings/*` (matches the audit's `react_route` column; Members is admin, **not** `/people/*`):

- `NAV_MEMBERS` → `/settings/members`
- `NAV_AUDIT_LOG` → `/settings/audit-log`
- `NAV_COMPANY_SETTINGS` → `/settings/company`
- `NAV_PERMISSIONS` → `/settings/permissions`
- `NAV_BACKUP_RESTORE` → `/settings/backup-restore`

People domain (`/customers`, `/vendors`, `/receivables`, `/payables`, `/workers`, `/partners`) contains **no** `/members` route. 1:1 `route_key → path`.

## 7. Contract tests (for the implementation slice)

- **Members owner-only:** `NAV_MEMBERS` ∈ the owner `_NAV_ROLE_PAGES` list and ∉ manager/cashier/partner/viewer.
- **Audit Log owner+manager:** `NAV_AUDIT_LOG` ∈ owner and manager lists; ∉ cashier/partner/viewer.
- **People hub = records only:** after the move, `_MOBILE_HUB_CONFIG["people"]` **excludes** `NAV_MEMBERS` and includes Customers/Vendors/Receivables/Payables/Workers/Partner Accounts.
- **Members on mobile under Admin:** after the move, `_MOBILE_HUB_CONFIG["more"]` admin section **includes** `NAV_MEMBERS`.
- **Settings admin-domain integrity:** accordion `settings` group == {Company Settings, Members, Permissions, Audit Log, Backup & Restore}; config pages owner-only; Audit Log the documented manager-visible exception.
- **React 1:1:** `/settings/members` and `/settings/audit-log` are unique and there is no `/people/members`.

## 8. Implementation slices (for Cursor — DO NOT implement yet)

- **NAV-UX-02-S4-IMPL-1 — mobile Members relocation:** **Implemented (2026-06)** — moved `NAV_MEMBERS` from `_MOBILE_HUB_CONFIG["people"]` → `_MOBILE_HUB_CONFIG["more"]` admin section (after Company Settings); desktop unchanged; contract tests in `tests/test_nav_ux_02_s4_members_audit_structural_contract.py`. No role change, no route change.
- **NAV-UX-02-S4-IMPL-2 — codify the domain principles:** document Principle A (Settings = admin config + oversight) and Principle B (People = operational records) in the audit; add the Settings-integrity + People-records-only tests.
- **NAV-UX-02-S4-IMPL-3 — React route freeze:** freeze the §6 admin `/settings/*` map (Members under settings, not people) as the migration contract.
- **(No slice) Audit Log role:** confirmed staying owner+manager — no change required.

## 9. Risk assessment

**LOW.** No role gate changes, no route deletion, no render change, no accounting impact. The only user-facing effect is the **mobile relocation of Members** (People hub → More/Admin), which corrects a domain mismatch. Residual risk: existing mobile users' muscle memory (Members previously under People) — mitigate by placing it clearly under More→Admin and, if desired, a short-lived note; desktop is unchanged so desktop users are unaffected. Audit Log keeps its current placement and (intentionally) its manager visibility.

## No-change statement (NAV-UX-02-S4 planning)

- **No UI change, no route deleted, no role changed, no cleanup, no `app.py` edit.** Exposure map + purpose classification + ownership model + role-gate recommendation + consistency recommendation + React contract + contract tests + slices + risk only; execution is the separately-approved NAV-UX-02-S4-IMPL slices.

---

*Planning only. Members is Settings(admin) on desktop but People hub on mobile; Audit Log is owner+manager (a role outlier inside the otherwise owner-only Settings group). Purpose: Members = access administration (system users), Audit Log = read-only oversight — both belong to the Settings/Admin domain; the People hub is for operational people *records* only. Recommend: move Members on mobile from People → More/Admin to match desktop ownership; keep Members owner-only; keep Audit Log manager-visible (read-only, low risk); Settings = admin domain = owner-only config + the documented manager-visible Audit Log oversight exception. React contract freezes Members at /settings/members (not /people/members) and Audit Log at /settings/audit-log, 1:1. Contract tests pin the gates, People-records-only, Members-under-Admin-on-mobile, and Settings integrity. Risk LOW — only a mobile relocation; no role/route/render change.*
