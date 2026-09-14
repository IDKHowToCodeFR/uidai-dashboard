# UIDAI Dashboard: Architecture Deep Dive

## 1. End-to-End Execution Lifecycle

### 1.1 Data Entry Point
- **Manual Path:** Client UI (Dash) -> `ApiClient` (session pooling, header injection) -> FastAPI `/upload` route via POST.
- **Automated Path:** APScheduler background worker (3-min interval). Queries SQLite `Setting` table via `ActiveFoldersConfig` to identify active watch directories. Scans local filesystem (`uidai_data/ccf_data`, `uidai_data/unimate_data`) for files missing in `FileMetadata`. Dispatches unindexed files to ingestion worker.

### 1.2 Processing & Transformation (Asynchronous ETL)
- **Streaming Handshake:** Client establishes WebSocket connection (`/ws/progress/{client_id}`) prior to POST. Prevents UI blocking during 50MB workbook processing.
- **Domain Parsers (`CCFParser`, `UniMateParser`):** Stateless, pure functions. 
  - Iterates OpenPyXL multi-sheet workbooks.
  - Performs column whitespace sanitization, type coercion, missing value imputation.
  - Applies vectorized Numpy computations for SLA status, Average Handle Time (AHT) thresholds, and Hold Time penalties.
  - Resolves vendor attribution dynamically via Dialed Number Identification Service (DNIS) prefix rules (`56*` -> Digitech). Converts `HH:MM:SS` strings to absolute seconds.
- **Worker Progress:** Background task pushes realtime completion % and status steps over WebSocket to client.

### 1.3 Storage & Persistence
- **Repository Seam (`CCFDatabaseRepo`, `UniMateDatabaseRepo`):** Receives clean DataFrame. Manages I/O transaction bounds.
- **Batching:** Executes SQLite inserts in chunked batches (1000 rows/batch) to optimize memory and lock contention.
- **Idempotency:** Uses `ON CONFLICT DO UPDATE` on composite unique constraints. 
  - CCF: `(company, language, call_timestamp)`. 
  - UniMate: `(ucid)`.
- **Provenance Registration:** Inserts `FileMetadata` record (filename, size, timestamp) and `AuditLog` (action, forwarded IP, User-Agent) within the same transaction block.

### 1.4 Output & UI Delivery
- **Signal:** WebSocket emits 100% completion. Client triggers callbacks to refresh UI.
- **Data Fetch:** Dash UI requests updated records. Queries intercepted by FastAPI RBAC middleware.
- **Tenant Isolation:** JWT Bearer token decoded. `companies` claim extracted and injected into base SQL queries to enforce row-level tenant isolation.
- **Client Cache:** Results cached in browser memory (`dcc.Store`).
- **Interactive rendering:** Dash Context Switcher handles CCF vs UniMate routing. UI element clicks trigger bidirectional cross-filtering -> Pandas in-memory dataframe slicing -> Plotly / AG-Grid component re-renders.

---

## 2. Component Interactions & Design Decisions

- **Pure Domain Parsers vs Monolithic ETL**
  - *Why:* Mixing file I/O, business logic (SLA math), and DB transactions in a single script destroys testability. Extracting `CCFParser` as a stateless module taking a path and returning a DataFrame creates a highly testable, predictable boundary. Repositories handle the dirty I/O.
- **WebSocket Streaming Uploads**
  - *Why:* 50MB Excel files with 100K+ rows take 5-15s to parse. Synchronous REST POST requests risk gateway timeouts and freeze the browser. WS + Async Task decouples processing from the HTTP lifecycle, ensuring stable UX.
- **SQLite WAL Mode + Composite Index Upserts**
  - *Why:* Selected SQLite for zero-configuration deployment portability. Enabled WAL (Write-Ahead Logging) to permit concurrent reads during heavy background batch writes. Composite unique indices enforce strict idempotent upserts—if a vendor accidentally uploads the same file twice, data is updated, not duplicated, preventing metric inflation.
- **`ApiClient` Header Forwarding**
  - *Why:* Because the Dash frontend and FastAPI backend run in the same deployment but communicate over local HTTP, standard FastAPI request objects record `127.0.0.1`. The custom `ApiClient` extracts `X-Forwarded-For` and `User-Agent` from the initial browser request and forwards them to the API for accurate non-repudiation audit logging.

---

## 3. Failure & Edge-Case Handling

- **Idempotent File Re-Uploads:** If a user re-uploads a previously processed file (or an overlapping date range), the composite unique constraints at the database level (`ON CONFLICT DO UPDATE`) catch the collision. Existing interval records are overwritten rather than duplicated, preventing arithmetic distortion of Service Level or Volume metrics.
- **Deprecated Cryptography (Lazy Password Upgrading):** If a user logs in with a password hashed using an older algorithm/work factor, the authentication module checks `needs_update()`. Upon successful verification, it generates a new bcrypt hash and updates the DB record transparently, securing the account without forcing a password reset.
- **Malformed Vendor Data:** Spreadsheets often contain missing columns, trailing spaces in headers, or null rows. Domain parsers explicitly map dictionary columns, execute aggressive whitespace stripping (`.strip()`), and utilize Pandas imputation strategies before applying vectorized math.
- **Abandoned Sessions:** Dash implements a clientside inactivity timer. If no mouse/keyboard activity is detected for 30 minutes, an overlay modal is triggered and the session token is aggressively cleared to prevent unauthorized terminal access.
- **Log Rot Rot:** To prevent SQLite bloat from heavy audit logging, an automated startup routine prunes `AuditLog` records older than 90 days.
