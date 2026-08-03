import requests

# Global session to pool HTTP connections and speed up communication with FastAPI
http_session = requests.Session()
