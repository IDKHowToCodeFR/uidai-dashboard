# UIDAI Contact Center Operations & Analytics Platform
## System Architecture & Technical Deep-Dive Specification

> **Document Classification:** Engineering Architecture & Operational Blueprint  
> **Target Audience:** Technical Leadership, System Architects, Core Engineering Team  
> **Status:** Active / Production-Ready  
> **Last Updated:** August 2026

---

## 1. Executive Summary & System Vision

The **UIDAI Contact Center Operations & Analytics Platform** is a specialized, multi-tenant analytics and operational intelligence system engineered to ingest, analyze, monitor, and audit national-scale Contact Center Facility (CCF) operations and interactive voice response (IVR/UniMate) customer journeys.

The platform bridges high-volume contact center operational telemetry (call volumes, agent handle times, service level agreements, abandoned call rates, IVR journeys) and executive reporting. It features a distributed architecture combining a **FastAPI backend** (asynchronous ETL pipeline, pure domain parsing engines, repository-backed idempotent upserts, RBAC, provenance audit logging, dynamic directory scheduling) with an **interactive Dash/Plotly analytical frontend** (featuring dynamic context switching, multi-page analytics, client-side session protection, and AG-Grid data exploration).

```mermaid
graph TB
    subgraph ClientLayer ["Client & Presentation Layer (Dash / Plotly :8050)"]
        Browser["User Browser (Dash / Plotly / AG-Grid)"]
        ContextSwitch["Context Switcher (CCF vs UniMate)"]
        WSClient["Clientside WebSocket Handler"]
    end

    subgraph APILayer ["API & Service Gateway (FastAPI :8000)"]
        Router["FastAPI Gateway (/users, /data, /settings, /ws)"]
        AuthModule["Auth & Security Engine (JWT / Bcrypt / Provenance)"]
        WSManager["WebSocket Connection Manager (/ws/progress/{client_id})"]
        
        subgraph IngestionPipeline ["Domain Ingestion & Processing Pipeline"]
            CCFParserEngine["CCFParser (Pure Domain Logic)"]
            UniMateParserEngine["UniMateParser (Pure Domain Logic)"]
            CCFRepo["CCFDatabaseRepo (Batch Upsert)"]
            UniMateRepo["UniMateDatabaseRepo (Batch Upsert)"]
        end
        
        CronEngine["Background Cron Scheduler (APScheduler - 3 min sweep)"]
        ActiveConfig["ActiveFoldersConfig (DB Setting Driven)"]
    end

    subgraph StorageLayer ["Persistence & Storage Layer"]
        RelationalDB[("Relational DB (SQLite WAL / PostgreSQL)")]
        FileStore[("Raw File Storage (uidai_data/ccf_data, uidai_data/unimate_data)")]
    end

    Browser -->|HTTP/REST Token Bearer| Router
    Browser <-->|WebSocket Progress Stream| WSManager
    WSClient <-->|Live Stream| WSManager
    Router --> AuthModule
    Router --> IngestionPipeline
    WSManager -.->|Real-Time Progress Broadcast| Browser
    IngestionPipeline -->|Vectorized Cleansing & Derivations| RelationalDB
    IngestionPipeline -->|Raw Excel Persistence| FileStore
    CronEngine -->|Dynamic Folder Sweep| ActiveConfig
    ActiveConfig -->|Filtered Ingestion| IngestionPipeline
```

---

## 2. High-Level Architecture & System Boundaries

### 2.1 System Context

```mermaid
graph LR
    subgraph Users ["Actors & Stakeholders"]
        AdminUser["System Administrator"]
        AnalystUser["Agency Analyst / Supervisor"]
        Vendors["Contact Center Vendors (Digitech / NSB)"]
    end

    subgraph CorePlatform ["UIDAI Operations Platform"]
        PlatformGateway["Ingestion, Analytics, RBAC & Audit Engine"]
    end

    Vendors -->|"Uploads Raw CCF Logs & UniMate Telemetry (.xlsx / .xls)"| PlatformGateway
    AdminUser -->|"Configures Active Folders, RBAC, SLA Rules & Audits Logs"| PlatformGateway
    AnalystUser -->|"Analyzes Cross-Vendor Trends & Exports PDF/Excel Reports"| PlatformGateway
```

### 2.2 Container Topology

```mermaid
graph TB
    subgraph FrontendApp ["Frontend Container (Dash / Python :8050)"]
        UI_Context["Global Context Switcher (CCF vs UniMate)"]
        UI_Pages["Multi-Page Routing (Dashboard, Comparison, Hourly, Raw Data, Admin)"]
        UI_State["Session & Memory State Stores (dcc.Store)"]
        UI_Client["API Client (Requests Session + Connection Pooling + Provenance Headers)"]
        UI_WS["Clientside WebSocket Handler (Vanilla JS)"]
        UI_Export["ReportLab PDF & Excel Streaming Client"]
    end

    subgraph BackendApp ["Backend API Container (FastAPI / Uvicorn :8000)"]
        API_Auth["OAuth2, Lazy Bcrypt Upgrading & RBAC Middleware"]
        API_Upload["Async Ingestion Router (/upload, /history, /data)"]
        API_Users["User Management Router (/users)"]
        API_Settings["Dynamic Settings Router (/settings)"]
        API_WS["Async WebSocket Manager (/ws/progress)"]
        API_Sched["APScheduler Background Worker (3-Minute Dynamic Sweep)"]
    end

    subgraph DataTier ["Data Tier"]
        DB[("Relational Store (uidai.db - SQLite WAL Mode)")]
        DiskFS[("File System (uidai_data/ccf_data, uidai_data/unimate_data)")]
    end

    UI_Context --> UI_Pages
    UI_Pages --> UI_State
    UI_State --> UI_Client
    UI_WS <-->|WebSocket Stream| API_WS
    UI_Client -->|REST API Calls| API_Auth
    API_Auth --> API_Upload
    API_Auth --> API_Users
    API_Auth --> API_Settings
    API_Upload --> API_WS
    API_Upload --> DiskFS
    API_Upload --> DB
    API_Sched --> API_Upload
    API_Sched --> DB
```

---

## 3. Domain Model & Ubiquitous Language

The domain model follows strict Domain-Driven Design (DDD) principles:

| Domain Term | Canonical Definition | Mathematical / Logic Model |
| :--- | :--- | :--- |
| **Service Level (SL %)** | The percentage of answered calls connected within threshold (&le; 20s). | `SL % = (ACD_Calls_20s / (Call_Offered - ABAN_10s)) * 100` |
| **Weighted Average SL** | Period-level Service Level aggregated across all volume intervals rather than naive arithmetic mean. | `Sum(ACD_Calls_20s) / Sum(Call_Offered - ABAN_10s) * 100` |
| **Average Handle Time (AHT)** | Total time an agent spends processing a customer interaction across talk, hold, and after-call work. | `AHT = (Talk_Time + Hold_Time + ACW_Time) / Total_ACD_Calls` |
| **Average Hold Time** | Average duration a caller is placed on hold per answered interaction. | `Avg_Hold = Total_Hold_Time / Total_ACD_Calls` |
| **Answer Rate** | Proportion of offered calls successfully answered by agents. | `Answer_Rate = (Total_ACD_Calls / Total_Call_Offered) * 100` |
| **SLA Score Thresholds** | Operational grading rules distinguishing healthy performance from contract penalty breaches. | &bull; `SL % > 85%` &rarr; Good, else Penalty<br>&bull; `AHT <= 240s` &rarr; Good, else Penalty<br>&bull; `Avg Hold <= 20s` &rarr; Good, else Penalty |
| **DNIS Company Mapping** | Identification of vendor attribution in UniMate IVR streams based on dialed number prefix. | &bull; `DNIS starts with 56` &rarr; Digitech<br>&bull; `DNIS starts with 57` &rarr; NSB<br>&bull; Others &rarr; Unknown |
| **Dynamic Time Bucketing** | Automated time-series aggregation resolution based on selected date ranges. | `≤7d` &rarr; Daily; `>31d` &rarr; Weekly (`W-MON`); `>90d` &rarr; Monthly (`MS`). |
| **Tenant Isolation** | Scoped data accessibility where tenant metrics are segmented at query time. | Query filtering constrained by JWT token claims (`companies` attribute). |
| **Lazy Password Upgrading** | Transparent cryptographic re-hashing upon login to update deprecated hashes. | Re-hashes on verified match if algorithm upgrade flag (`needs_update()`) is active. |
| **Provenance Audit Trail** | Strict attribution of system operations with forwarded client IP, user agent, and endpoint. | Captures `X-Forwarded-For`, `User-Agent`, action, and timestamp in `AuditLog`. |

---

## 4. Deep Module Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Router Layer                     │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Clean Interface)
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               Deep Domain Ingestion Modules                 │
├─────────────────────────────────────────────────────────────┤
│ • CCFParser / UniMateParser: Pure functional parsing        │
│   - Multi-sheet OpenPyXL parsing & concatenation            │
│   - Column sanitization & type coercion                     │
│   - Vectorized KPI derivations & SLA classification         │
│   - DNIS vendor mapping & duration normalization            │
├─────────────────────────────────────────────────────────────┤
│ • CCFDatabaseRepo / UniMateDatabaseRepo: Persistence Seam   │
│   - Chunked batch execution (batch_size=1000)               │
│   - ON CONFLICT DO UPDATE composite index idempotency       │
│   - Transactional metadata registration                     │
├─────────────────────────────────────────────────────────────┤
│ • WebSocket Connection Manager: Streaming Layer             │
│   - Real-time percentage & status updates                   │
└─────────────────────────────────────────────────────────────┘
```

### 4.1 Module Summary Table

| Module Seam | Public Interface | Implementation Depth (Encapsulated Complexity) |
| :--- | :--- | :--- |
| **`auth_utils`** | `verify_and_upgrade_password()`, `get_current_user()`, `PermissionChecker()`, `add_log()`, `archive_old_logs()`, `extract_request_metadata()` | JWT encoding/decoding, passlib context switching, fallback bcrypt compatibility, request IP/User-Agent extraction, 90-day automatic log retention pruning. |
| **`CCFParser`** | `CCFParser.parse(save_path, progress_callback)` | Multi-sheet Excel workbook iteration, column whitespace stripping, missing value imputation, vectorized numpy SLA/AHT/Hold penalty derivations. |
| **`UniMateParser`** | `UniMateParser.parse(save_path, progress_callback)` | CSV/Excel parsing, DNIS-based vendor assignment (`56*` vs `57*`), time string duration conversion (`HH:MM:SS` &rarr; seconds), regional language code mapping. |
| **`CCFDatabaseRepo`** | `CCFDatabaseRepo.save_parsed_data(...)` | `FileMetadata` creation, column dictionary mapping, 1000-row chunked batch execution, SQLite `on_conflict_do_update` upsert on `(company, language, call_timestamp)`. |
| **`UniMateDatabaseRepo`** | `UniMateDatabaseRepo.save_parsed_data(...)` | `FileMetadata` creation, column dictionary mapping, 1000-row chunked batch execution, SQLite `on_conflict_do_update` upsert on `(ucid)`. |
| **`ActiveFoldersConfig`** | `ActiveFoldersConfig.get_active_folders(db)` | Dynamic DB settings query (`Setting` table key `active_folders`) with fallback to `['ccf_data', 'unimate_data']` for scheduled background sweeps. |
| **`api_client`** | `ApiClient.get_dataframe()`, `ApiClient.login()`, `ApiClient.upload_file()` | Session pooling (`requests.Session`), client header propagation (`X-Forwarded-For`, `User-Agent`), client-side LRU memory caching. |
| **`theme & export`** | `get_plotly_template()`, `make_header_with_download()`, `wrap_graph_with_download()`, `generate_pdf_report()` | PostHog-inspired design tokens, ReportLab programmatic PDF compilation, dynamic Excel export dropdown bindings, skeleton loaders. |

---

## 5. End-to-End Data & Execution Lifecycles

### 5.1 Ingestion & Asynchronous ETL Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor Client as User / Browser (Dash)
    participant WS as WebSocket (/ws/progress/{client_id})
    participant API as FastAPI Gateway (/upload)
    participant Disk as Raw File System (uidai_data/)
    participant Worker as Background Task
    participant Parser as Domain Parser (CCF / UniMate)
    participant Repo as DB Repository (CCF / UniMate)
    participant DB as SQLite Relational Database

    Client->>WS: Connect WebSocket (client_id)
    WS-->>Client: Connection Accepted
    Client->>API: POST /upload (File + client_id + data_type)
    API->>Disk: Persist raw Excel/CSV file to directory
    API->>Worker: Dispatch process_file_background (Async Task)
    API-->>Client: HTTP 200 {"status": "processing"}

    Worker->>WS: Broadcast Progress 10% (Parsing file...)
    Worker->>Parser: parse(save_path, progress_callback)
    Parser->>Parser: OpenPyXL Sheet Iteration / CSV Read
    Worker->>WS: Broadcast Progress 60% (Cleaning & Deriving KPIs...)
    Parser->>Parser: Vectorized KPI Computations (SLA, AHT, DNIS Mapping)
    Parser-->>Worker: Cleaned DataFrame
    Worker->>WS: Broadcast Progress 90% (Inserting into database...)
    Worker->>Repo: save_parsed_data(db, df, ...)
    Repo->>DB: Insert FileMetadata record
    Repo->>DB: Chunked ON CONFLICT DO UPDATE Upsert (1000 rows/batch)
    Repo->>DB: Insert AuditLog (FILE_UPLOADED + Metadata)
    Worker->>WS: Broadcast Progress 100% (Complete)
    WS-->>Client: Triggers Client-side UI Refresh & Notification
```

### 5.2 Background Scheduled Directory Sweep Lifecycle

```mermaid
sequenceDiagram
    autonumber
    participant Sched as APScheduler (Every 3 Minutes)
    participant Config as ActiveFoldersConfig
    participant DB as SQLite Database
    participant Disk as File System (uidai_data/)
    participant Worker as process_file_background

    Sched->>DB: Query indexed files {(filename, upload_directory)}
    Sched->>Config: get_active_folders(db)
    Config->>DB: Query Setting (key='active_folders')
    DB-->>Config: Active Folders List ['ccf_data', 'unimate_data']
    Sched->>Disk: Scan subdirectories for unindexed files
    loop For each unindexed file
        Sched->>Worker: process_file_background(file_path, filename, "CRON", "system_cron", data_type)
        Worker->>DB: Parse & Ingest Records via Repository
    end
```

### 5.3 Authentication, Session & Inactivity Lifecycle

```mermaid
sequenceDiagram
    autonumber
    actor User as Client Browser
    participant Auth as Auth Endpoint (/login)
    participant DB as SQLite / PostgreSQL
    participant Crypt as Password Context (Bcrypt)

    User->>Auth: POST /login (username, password)
    Auth->>DB: Query User by username
    DB-->>Auth: User Record (password_hash, companies, permissions)
    Auth->>Crypt: verify(plain, hash)
    Crypt-->>Auth: Password Valid
    opt Hash Needs Update (Algorithm Upgrade)
        Auth->>Crypt: Generate updated bcrypt hash
        Auth->>DB: Update user.password_hash (Lazy Upgrade)
    end
    Auth->>DB: Increment login_count, update last_login
    Auth->>DB: Insert AuditLog (LOGIN_SUCCESS + IP/UserAgent)
    Auth-->>User: JWT Bearer Token (username, role, permissions, companies)
    Note over User: Dash clientside timer monitors activity.<br/>30 min inactivity triggers Inactivity Modal & Logout.
```

---

## 6. Database Schema & Relational Models

```mermaid
erDiagram
    User ||--o{ UserPermission : "has"
    User {
        int id PK
        string username UK
        string password_hash
        json companies
        int login_count
        string last_login
    }

    UserPermission {
        int id PK
        int user_id FK
        string permission_name
    }

    AuditLog {
        int id PK
        string timestamp
        string action
        string username
        string details
        string ip_address
        string user_agent
        string endpoint
    }

    Setting {
        string key PK
        json value
    }

    FileMetadata ||--o{ CCFData : "contains"
    FileMetadata ||--o{ UniMateData : "contains"
    FileMetadata {
        int id PK
        string filename
        string upload_directory
        string data_type
        string uploaded_at
        string uploader
        int size_bytes
    }

    CCFData {
        int id PK
        int file_id FK
        string company
        string language
        string date_logged
        string call_timestamp
        string day
        float call_offered
        float aban_calls_10_sec
        float acd_calls_10_sec
        float acd_calls_20_sec
        float aban_calls
        float held_calls
        float service_level_pct
        string service_level_status
        float acd_calls
        float hold_time
        float avg_hold_time
        string hold_time_status
        float acd_time
        float acw_time
        float avg_handle_time
        string aht_status
    }

    UniMateData {
        int id PK
        int file_id FK
        string ucid UK
        string session_id
        string company
        string day_of_week
        string call_start_time
        string call_end_time
        int call_duration
        string ani
        string dnis
        string language
        string authentication
        string auth_mechanism
        string termination_type
        string termination_reason
        string description
        string region
    }
```

### 6.1 Table Constraint Details

- **`FileMetadata`**: Unique constraint on `(filename, upload_directory)` ensures distinct file tracking across separate data directories.
- **`CCFData`**: Unique composite constraint on `(company, language, call_timestamp)` guarantees idempotent re-upload and prevents duplicate interval inflation.
- **`UniMateData`**: Unique constraint on `(ucid)` guarantees idempotency for call-level IVR records.
- **`Setting`**: Key-value JSON store for system configuration (e.g., `active_folders`).

---

## 7. Architectural Decision Records (ADRs)

### ADR 0001: Asynchronous WebSocket Progress Streaming
* **Context**: Uploading multi-sheet 50MB workbooks with 100,000+ rows takes 5–15s. Synchronous HTTP POST blocks the client and risks connection timeouts.
* **Decision**: Adopt a dual-channel upload pattern: the client establishes a WebSocket connection with `client_id`, then fires an async POST. FastAPI spawns a background worker broadcasting real-time progress percentages over WebSocket.
* **Consequences**: Zero UI freezing, predictable user feedback, decoupled HTTP request timeout risks.

### ADR 0002: Relational Metrics Storage with Unique Composite Constraints
* **Context**: CCF operational logs are frequently re-uploaded with overlapping date ranges or revisions.
* **Decision**: Store all normalized records in a single relational table (`ccf_data`) constrained by `(company, language, call_timestamp)` and `unimate_data` constrained by `(ucid)`. Perform batch upserts using SQLite `on_conflict_do_update`.
* **Consequences**: Full idempotency during file re-uploads; prevents duplicate record inflation.

### ADR 0003: Connection-Forwarded Audit Logging with Provenance
* **Context**: The frontend communicates with the backend via an internal network client (`ApiClient`), which causes standard backend logging to record `127.0.0.1`.
* **Decision**: `ApiClient` extracts client request headers (`X-Forwarded-For`, `User-Agent`) and forwards them to FastAPI headers. Backend `extract_request_metadata()` captures true client origin.
* **Consequences**: Non-repudiation audit trails for compliance-sensitive operations.

### ADR 0004: Pure Domain Parsers & Repository Pattern Separation
* **Context**: Mixing file parsing, data cleaning, derived KPI computation, and database I/O in a single monolith causes high cognitive friction and impairs testability.
* **Decision**: Decompose dataset ingestion into pure domain parsers (`CCFParser`, `UniMateParser`) that return clean DataFrames, and dedicated persistence repositories (`CCFDatabaseRepo`, `UniMateDatabaseRepo`) that manage database transactions and batch upserts.
* **Consequences**: High leverage, clear seams, simplified unit testing, and straightforward addition of future datasets.

### ADR 0005: Dynamic DB-Configured Directory Sweep for Automated Ingestion
* **Context**: Contact center vendor files are dropped periodically into directory paths on the server. Hardcoding ingestion folders prevents dynamic administration.
* **Decision**: APScheduler runs every 3 minutes, reading enabled folders dynamically from the `Setting` table via `ActiveFoldersConfig`, scanning unindexed files, and triggering ingestion.
* **Consequences**: Zero downtime folder management; hands-free automated ingestion.

---

## 8. Production Hardware, Sizing & Kernel Tuning Profile

Designed for **1,000 concurrent sessions**:

- **Compute**: 4–8 vCPUs (Ubuntu 22.04 LTS or newer)
- **Memory**: 8GB – 16GB RAM (Optimized for in-memory Pandas dataframe slicing and Plotly rendering)
- **Storage**: 50GB+ Enterprise NVMe SSD (High IOPS for SQLite WAL operations)
- **Kernel Tuning (`/etc/sysctl.conf`)**:
  - `fs.file-max = 65535`
  - `net.ipv4.tcp_max_syn_backlog = 4096`
  - `net.ipv4.tcp_fin_timeout = 15`
- **Resource Limits (`/etc/security/limits.conf`)**:
  - `* soft nofile 65535`
  - `* hard nofile 65535`
- **Network Ports**:
  - `80` (HTTP), `443` (HTTPS/WSS) via Nginx Reverse Proxy
  - Internal Only: `8000` (FastAPI), `8050` (Dash)
