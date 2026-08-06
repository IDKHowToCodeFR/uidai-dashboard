# Glossary

- **Permissions**: Granular capabilities assigned to an identity. Core permissions include:
  - `can_view_global`: Can view data across all companies.
  - `can_view_scoped`: Can only view data specific to their assigned identity.
  - `can_upload_files`: Can upload new data files to the system.
  - `can_download_files`: Can download/export data files.
- **Dash (Frontend)**: The presentation layer. Renders UI and fetches data via API.
- **FastAPI (Backend)**: The API layer. Handles auth, role-based data filtering, file parsing, and state management. Backed by **PostgreSQL** for scalable concurrent data storage.
- **Session**: Connection pooling on the frontend to reuse HTTP connections, reducing latency.
- **Cache**: In-memory caching (`lru_cache`) on the backend to avoid repetitive disk/database reads for frequently requested data.
- **Tenant Isolation**: Single storage directory (`data/processed/`). Filenames prefixed with `role_`. Data filtered by `company_id` (`user_role`) on read. No per-company subdirectories.
- **Weighted Average SL (Service Level)**: Calculated by aggregating all call volumes across all intervals for a period before determining the percentage, ensuring statistical accuracy over simple unweighted averages.
- **Dynamic Time Bucketing**: A senior-level visualization pattern that automatically resamples time-series data into Daily, Weekly (W-MON), or Monthly (MS) buckets based on the total selected date range (e.g., >31 days = Weekly). It also floors timestamps (`dt.floor('D')`) to eliminate intraday noise from trend charts.
- **AHT Breakdown**: The decomposition of Average Handle Time into Talk Time, Hold Time, and Wrap Time (ACW).
- **Answer Rate**: The percentage of calls successfully answered by agents out of the total calls offered.

## Future Architecture (Parked Ideas)

- **Multi-Tenant RBAC**: Transitioning from a flat admin structure to a hierarchical one (Super Admin -> Tenant Admin -> Tenant User). This will require a DB schema update (adding Tenant IDs, Roles) and separate dashboards. Parked to avoid over-engineering for <50 users.
- **OTP & Password Verification**: Explicitly rejected. Since the dashboard is for internal use only, strict 2FA/OTP introduces unnecessary friction and will not be built.
- **Safe Deletion Protocol**: A GitHub-style confirmation modal requiring the Admin to type the exact company name before a destructive Deactivation API call can be fired.

## Design System & Visual Language

- **Semantic Color Palette**: The dashboard strictly adheres to an authoritative, semantic color scheme suitable for an operational BPO environment. Colors are not used purely for aesthetics; they communicate state:
  - **Negative/Action Required**: Red (`#ef4444`) for Abandonment, SLA breaches, and excessive Hold Times.
  - **Positive/Success**: Emerald Green (`#10b981`) or Tech Blue (`#3b82f6`) for Answered calls, SLAs met, and productive Talk Time.
  - **Neutral/Baseline**: Slate Grays (`#e2e8f0`, `#94a3b8`, `#64748b`) for Call Volume (Offered), Wrap Time (ACW), and background elements.

## Known Technical Debt (To Fix Later)

- **Frontend Memory Caching (Dash `dcc.Store`)**: We have agreed to migrate from client-side JSON memory caching to Server-Side Caching using **Redis** to avoid freezing the browser and choking the network as data scales. Redis will also be used to enforce single active sessions across the load-balanced servers.
- **Backend DB Concurrency (Race Condition)**: We have agreed to migrate from raw JSON files (`users.json`, `logs.json`) to PostgreSQL to resolve concurrency issues across load-balanced servers.
