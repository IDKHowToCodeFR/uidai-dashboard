# UIDAI Dashboard

A unified dashboard for analyzing call center data. 
The application uses a unified architecture where the Dash frontend is mounted directly onto the FastAPI backend, running on a single port for seamless deployment.

## Installation

1. Clone the repository:
```bash
git clone https://gitlab.com/lazy3915830/uidai-dashbard/
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


or 
```bash
uv init 
uv add -r requirements.txt 
uv sync 
uv lock
```
or 
```bash
./start_all.bat 
```

## Running the Application

To run the application, simply execute the root start script:

```bash
python run.py
```
or 
```bash
./start_all.bat
```
Or, if you are on Windows, you can double-click `start_all.bat`.

The unified server will start on port 8000. 
Open your browser and navigate to:
**http://localhost:8000**

## Database & Errors
- The application uses an SQLite database (`uidai.db`). 
- On first startup, it will automatically initialize the schema and create default accounts (`admin` / `admin`).
- **If you get Alembic migration errors (e.g., UNIQUE constraint failed)** when cloning and running, just delete `uidai.db` and let it recreate. The startup check will now properly stamp a new database to avoid these constraint errors.
- **Secret Key:** Make sure your `.env` contains `SECRET_KEY=UIDAI_HQ_SPECIAL_PRIVATE_KEY`.

## Sample Data Generation
By default, the system will only create the necessary upload folders (`uidai_data/ccf_data`, `cdr_data`, etc.) without generating sample `.csv` or `.xlsx` files inside them. 
If you want to auto-generate sample files for testing, open `backend/main.py`, search for `ensure_sample_data()` and uncomment this line:
```python
threading.Thread(target=generate_data, daemon=True).start()
```
