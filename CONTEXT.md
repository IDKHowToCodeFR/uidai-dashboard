# Glossary & Ubiquitous Language
- **Vendor**: A third-party operator handling calls for the contact center (e.g., Digitech, NSB). Replaces "agency" or "company" for consistency. Vendor identification is extracted from raw data (e.g., parsing the first digit of the `split1` column in CDR) because raw files strictly omit explicit Vendor columns.
- **Datasets**: CDR, Unimate, and CCF data streams are treated as completely independent sources for aggregated visualizations. There is no requirement to join them at the individual call/session level (e.g., linking UCID to Call ID).
- **Permissions**: Granular capabilities assigned to an identity.
  - `can_view_global`: Can view all data.
  - `can_view_scoped`: Can only view assigned data.
  - `can_upload_files`: Can upload data.
  - `can_download_files`: Can download data.
- **Roles**:
  - `Admin`: Single protected administrator account (`admin`) managing users, permissions, global settings, and audit logs. Protected against self-deactivation and privilege removal.
  - `User`: Standard user with scoped capabilities governed by assigned permissions and company restrictions.
- **CCF Data (Contact Center Facility)**: High-volume interval metrics capturing queue telephony (Offered, Answered, Abandoned, Talk Time, Hold Time, Wrap Time, SLA %).
- **UniMate Data (IVR & Journey Telemetry)**: Granular call-level telemetry records tracking citizen journey stages through the interactive voice response system.
- **UCID (Universal Call Identifier)**: Unique identifier for an individual call interaction within UniMate telemetry, serving as the primary idempotency key.
- **DNIS Company Resolution**: Automated vendor attribution for UniMate call streams derived from the Dialed Number Identification Service prefix (`56*` &rarr; Digitech, `57*` &rarr; NSB).
- **Service Level (SL %)**: Percentage of answered calls connected within the designated SLA threshold (&le; 20s). Mathematical model: `SL % = (ACD_20s / (Call_Offered - ABAN_10s)) * 100`.
- **Weighted Average SL**: Period-level Service Level calculated by summing answered calls within threshold divided by net offered calls across all intervals, preventing statistical distortion from arithmetic averages.
- **Average Handle Time (AHT)**: Total time spent handling an interaction across talk time, hold time, and after-call work (ACW) per answered call. Threshold: `≤ 240s` is Good; `> 240s` breaches SLA.
- **Average Hold Time**: Average duration a caller is placed on hold per answered call. Threshold: `≤ 20s` is Good; `> 20s` breaches SLA.
- **Answer Rate**: Percentage of calls offered that were successfully answered by agents (`Total_ACD / Total_Offered * 100`).
- **Dynamic Time Bucketing**: Automated resampling of time-series visual trends into Daily (`≤ 7d`), Weekly (`> 31d`), or Monthly (`> 90d`) buckets based on selected query range, with timestamp floor normalization.
- **Temporal Preset Pills**: Segmented 1-click filter controls (`Today`, `Yesterday`, `Last 7D`, `MTD`, `YTD`, `Custom`) that instantly set query dates and synchronize the active resolution badge.
- **Resolution Badge**: Visual indicator in the filter bar reflecting the current time-series aggregation level (Daily, Weekly, Monthly) applied to trend charts.
- **Operational KPI Cards**: Structured metric cards displaying high-impact values, period-over-period comparative delta chips, explicit contract SLA benchmark status tags, and mini trend sparklines.
- **Bidirectional Chart Cross-Filtering**: Interactive behavior where clicking chart elements (bars, pie slices, trends) dynamically isolates that dimension across all charts, synchronized with clearable active filter chips.
- **Active Filter Chips**: Dismissible badges displayed in the sticky control bar representing active cross-filters, allowing one-click removal of specific filters.
- **Tenant Isolation (Database)**: Row-level tenant data filtering at query time constrained by JWT claims (`companies` attribute) against normalized `ccf_data` and `unimate_data` tables.
- **Context Switcher**: Pinned UI control at the top of the persistent navigation bar toggling the active analytics workspace between CCF Analytics and UniMate Analytics.
- **Sticky In-Page Filter Bar**: Persistent top-level control bar containing Date Presets, Company Multi-Select, and Language filters for zero-click-overhead operational adjustments.
- **Lazy Upgrading (Password Hashing)**: Transparent re-hashing of credentials into the newest configured algorithm upon successful login.
- **Provenance Audit Logging**: Non-repudiation audit trail recording operator identity, action, timestamp, target endpoint, and forwarded client provenance (`X-Forwarded-For`, `User-Agent`).
- **Active Folders Config**: Database-driven configuration (`Setting` table key `active_folders`) determining which filesystem subdirectories are monitored by the scheduled cron ingestion worker.

## Architectural Seams & Patterns

- **Pure Parser Modules (`CCFParser`, `UniMateParser`)**: Stateless domain parsers handling multi-sheet workbook extraction, type coercion, duration calculation, and vectorized KPI computation.
- **Database Repositories (`CCFDatabaseRepo`, `UniMateDatabaseRepo`)**: Dedicated persistence modules managing metadata tracking, chunked batching, and composite key upsert execution.
- **Dual-Channel WebSocket Ingestion**: Non-blocking upload mechanism where background processing threads stream real-time percentage and step progress to the Dash client over WebSocket.
- **Dynamic Ingestion Sweep**: Background APScheduler worker executing every 3 minutes to automatically ingest new unindexed files from active folders.
- **90-Day Log Archiving**: Automated cleanup routine pruning audit records older than 90 days during application startup.

## Design System & Visual Language

- **Semantic Color Palette**: Strict operational color palette communicating operational status:
  - **Negative / Action Required**: Red (`#ef4444`) for Abandonment, SLA penalties, and hold time breaches.
  - **Positive / Success**: Emerald Green (`#10b981`) or Tech Blue (`#3b82f6`) for Answered calls, SLA compliance, and productive Talk Time.
  - **Neutral / Baseline**: Slate Grays (`#e2e8f0`, `#94a3b8`, `#64748b`) for Call Volume (Offered), Wrap Time (ACW), and structural layout.

## Future Architecture & Parked Ideas

- **OTP & Password Verification**: Explicitly rejected. Internal dashboard environment makes strict 2FA/OTP unnecessary friction.
- **Safe Deletion Protocol**: GitHub-style confirmation modal requiring user to type exact username/company before deactivation.
- **Server-Side Caching (Redis)**: Future migration from client-side `dcc.Store` memory caching to Redis to support horizontally scaled workers.
