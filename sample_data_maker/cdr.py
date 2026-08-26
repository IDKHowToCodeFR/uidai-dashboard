import pandas as pd
import random
import uuid
from datetime import datetime, timedelta
import os

# Ensure the uidai_data/cdr_data directory exists
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uidai_data', 'cdr_data')
os.makedirs(output_dir, exist_ok=True)

# Define constants
# Language code mapping (split1 encodes vendor + language as a 3-digit code)
# First digit: 8 = Digitech, 9 = NSB
# Last two digits: language code
LANGUAGE_CODES = {
    "11": "Hindi",
    "12": "English",
    "13": "Bengali",
    "14": "Telugu",
    "15": "Marathi",
    "16": "Tamil",
    "17": "Gujarati",
    "18": "Kannada",
    "19": "Odia",
    "20": "Malayalam",
    "21": "Punjabi",
    "22": "Assamese",
}

# Population-based weights matching the same 12 languages in order
# Hindi >> English > Bengali > Telugu ~ Marathi > Tamil > Gujarati > Kannada > Odia ~ Punjabi ~ Malayalam > Assamese
LANG_CODES_LIST = list(LANGUAGE_CODES.keys())
LANG_WEIGHTS = [0.44, 0.18, 0.07, 0.05, 0.05, 0.05, 0.04, 0.03, 0.02, 0.02, 0.03, 0.02]


def generate_sample_cdr_data(num_records=1000, days=30):
    data = []
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Pre-generate a pool of ~50 agent logins per vendor for realism
    digitech_agents = [f"56{random.randint(10000, 99999)}" for _ in range(50)]
    nsb_agents = [f"57{random.randint(10000, 99999)}" for _ in range(50)]
    
    for _ in range(num_records):
        call_id = str(uuid.uuid4())
        
        # Call start time
        random_seconds = random.randint(0, days * 24 * 60 * 60)
        segstart = start_date + timedelta(seconds=random_seconds)
        
        # --- Time-of-day realism (matches CCF/UniMate patterns) ---
        hour = segstart.hour
        day_name = segstart.strftime("%A")
        
        if 9 <= hour <= 18:
            tod_multiplier = random.uniform(0.8, 1.3)
        elif 6 <= hour < 9 or 18 < hour <= 21:
            tod_multiplier = random.uniform(0.5, 0.9)
        else:
            # Late night / early morning: very few calls, mostly short/abandoned
            tod_multiplier = random.uniform(0.1, 0.4)
            
        # Weekend dip
        if day_name in ("Saturday", "Sunday"):
            tod_multiplier *= random.uniform(0.5, 0.7)
        
        # --- Realistic call timings ---
        # Talktime: most calls 30s-8min, occasional long calls up to 54min
        # Use lognormal for realistic heavy-tail distribution
        raw_talk = random.lognormvariate(4.5, 1.2)  # median ~90s, long tail
        talktime = max(0, min(int(raw_talk * tod_multiplier), 3240))
        
        # ACW (after-call work): typically 10-120s, skewed short
        acwtime = max(0, int(random.lognormvariate(3.2, 0.8) * tod_multiplier))
        acwtime = min(acwtime, 300)
        
        # Hold time: most calls no hold, some have 10-180s hold
        if random.random() < 0.35:  # 35% of calls have hold time
            ansholdtime = max(0, int(random.lognormvariate(3.0, 1.0)))
            ansholdtime = min(ansholdtime, 600)
        else:
            ansholdtime = 0
        
        # Duration = talk + acw + hold + ring/setup overhead
        ring_time = random.randint(5, 30)
        duration = talktime + acwtime + ansholdtime + ring_time
        
        segstop = segstart + timedelta(seconds=duration)
        
        # UTC times (IST = UTC+5:30)
        segstartutc = segstart - timedelta(hours=5, minutes=30)
        segstoputc = segstop - timedelta(hours=5, minutes=30)
        
        # --- Vendor & Language from split1 ---
        # Digitech (8xx) handles 60% of volume, NSB (9xx) handles 40%
        agency_code = random.choices(["8", "9"], weights=[0.6, 0.4], k=1)[0]
        lang_code = random.choices(LANG_CODES_LIST, weights=LANG_WEIGHTS, k=1)[0]
        split1 = f"{agency_code}{lang_code}"
        
        # --- Transfer / agent release logic ---
        # ~8% of calls get transferred (realistic for contact center)
        transferred = 1 if random.random() < 0.08 else 0
        
        if transferred == 1:
            agt_released = 1
        else:
            # ~90% of non-transferred calls release normally
            agt_released = 1 if random.random() < 0.90 else 0
            
        # Agent logins from the vendor's pool (reuse agents for realism)
        if agency_code == "8":
            anslogin = random.choice(digitech_agents)
            origlogin = random.choice(digitech_agents)
        else:
            anslogin = random.choice(nsb_agents)
            origlogin = random.choice(nsb_agents)
        
        data.append({
            "Call Id": call_id,
            "acwtime": acwtime,
            "ansholdtime": ansholdtime,
            "duration": duration,
            "segstart": segstart.strftime("%d-%m-%Y %H:%M:%S"),
            "segstartutc": segstartutc.strftime("%d-%m-%Y %H:%M:%S"),
            "segstop": segstop.strftime("%d-%m-%Y %H:%M:%S"),
            "segstoputc": segstoputc.strftime("%d-%m-%Y %H:%M:%S"),
            "talktime": talktime,
            "split1": split1,
            "transferred": transferred,
            "agt_released": agt_released,
            "origlogin": origlogin,
            "anslogin": anslogin
        })
        
    df = pd.DataFrame(data)
    
    # Sort by segstart for realistic flow
    df['temp_time'] = pd.to_datetime(df['segstart'], format="%d-%m-%Y %H:%M:%S")
    df = df.sort_values(by="temp_time").drop(columns=['temp_time'])
    
    # Save to Excel
    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"cdr_data_{current_time_str}.xlsx"
    file_path = os.path.join(output_dir, file_name)
    
    df.to_excel(file_path, index=False)
    print(f"Successfully generated {num_records} CDR sample records at {file_path}")

if __name__ == "__main__":
    n_input = input("Input rows (default 1000) : ")
    n = int(n_input) if n_input.strip() else 1000
    
    days_input = input("Input days (default 30) : ")
    days = int(days_input) if days_input.strip() else 30
    
    generate_sample_cdr_data(n, days)
