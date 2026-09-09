# UIDAI Dashboard

A unified dashboard for analyzing call center data. 
The application uses a unified architecture where the Dash frontend is mounted directly onto the FastAPI backend, running on a single port for seamless deployment.

## Installation

1. Clone the repository:
```bash
git clone <your-repo-url>
cd uidai_dashboard
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv .venv
# Activate the environment (Windows)
.venv\Scripts\activate
# Activate the environment (Linux/Mac)
source .venv/bin/activate

pip install -r requirements.txt
```

## Running the Application

To run the application, simply execute the root start script:

```bash
python run.py
```
Or, if you are on Windows, you can double-click `start_all.bat`.

The unified server will start on port 8000. 
Open your browser and navigate to:
**http://localhost:8000**

## Database

The application uses an SQLite database (`uidai.db`). 
- On first startup, it will automatically initialize the schema and create default accounts (`admin` / `admin`).
- If your database schema gets corrupted or out-of-sync, simply delete `uidai.db` and restart the server. It will automatically recreate itself perfectly.
