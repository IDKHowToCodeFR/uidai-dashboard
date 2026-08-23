# Glossary

- **Permissions**: Granular capabilities assigned to an identity.
  - `can_view_global`: Can view all data.
  - `can_view_scoped`: Can only view assigned data.
  - `can_upload_files`: Can upload data.
  - `can_download_files`: Can download data.
- **Roles**:
  - `Admin`: There is strictly only one admin account (`admin`) in the entire system. The admin can manage users and change their own password, but cannot deactivate themselves or strip their own admin privileges to prevent system lockouts.
  - `User`: Standard user with limited access based on permissions.
- **Dash (Frontend)**: The presentation layer. Renders UI and fetches data via API.
- **FastAPI (Backend)**: The API layer. Handles auth, role-based data filtering, file parsing, and state management. Backed by **PostgreSQL** for scalable concurrent data storage.
- **Session**: Connection pooling on the frontend to reuse HTTP connections, reducing latency.
- **Cache**: In-memory caching (`lru_cache`) on the backend to avoid repetitive disk/database reads for frequently requested data.
- **Tenant Isolation (Database)**: Replaces file-system isolation. All uploaded raw data is stored in a single unified metrics table (`call_metrics`), isolated by a `company_id` column. A separate metadata table (`files_metadata`) tracks upload history and lineage (`file_id`).
- **Context Switcher**: A global UI control (currently a pill-style toggle at the top of the sidebar) that dictates the active scope of the dashboard (e.g., CCF vs UniMate). It filters both the available navigation routes and the file history selection.
- **Weighted Average SL (Service Level)**: Calculated by aggregating all call volumes across all intervals for a period before determining the percentage, ensuring statistical accuracy over simple unweighted averages.
- **Dynamic Time Bucketing**: A senior-level visualization pattern that automatically resamples time-series data into Daily, Weekly (W-MON), or Monthly (MS) buckets based on the total selected date range (e.g., >31 days = Weekly). It also floors timestamps (`dt.floor('D')`) to eliminate intraday noise from trend charts.
- **AHT Breakdown**: The decomposition of Average Handle Time into Talk Time, Hold Time, and Wrap Time (ACW).
- **Answer Rate**: The percentage of calls successfully answered by agents out of the total calls offered.
- **Lazy Upgrading (Password Hashing)**: The process of transparently re-hashing a user's password into a newly configured algorithm during a successful login, allowing graceful deprecation of older hash algorithms.

## Future Architecture (Parked Ideas)

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
