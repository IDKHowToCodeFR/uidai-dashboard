# Glossary

- **Permissions**: Granular capabilities assigned to an identity. Core permissions include:
  - `can_view_global`: Can view data across all companies.
  - `can_view_scoped`: Can only view data specific to their assigned identity.
  - `can_upload_files`: Can upload new data files to the system.
- **Dash (Frontend)**: The presentation layer. Renders UI and fetches data via API.
- **FastAPI (Backend)**: The API layer. Handles auth, role-based data filtering, file parsing, and state management.
- **Session**: Connection pooling on the frontend to reuse HTTP connections, reducing latency.
- **Cache**: In-memory caching (`lru_cache`) on the backend to avoid repetitive disk/database reads for frequently requested data.
