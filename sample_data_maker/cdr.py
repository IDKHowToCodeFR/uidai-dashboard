import pandas as pd
import random
import uuid
from datetime import datetime, timedelta
import os

# Ensure the uidai_data/cdr_data directory exists
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uidai_data', 'cdr_data')
os.makedirs(output_dir, exist_ok=True)

# Define constants
# Languages codes (11 to 22 for 12 languages)
LANGUAGE_CODES = [str(i) for i in range(11, 23)] # 11 to 22

def generate_sample_cdr_data(num_records=1000, days=30):
    data = []
    
    start_date = datetime.now() - timedelta(days=days)
    
    for _ in range(num_records):
        call_id = str(uuid.uuid4())
        
        # Call start time
        random_seconds = random.randint(0, days * 24 * 60 * 60)
        segstart = start_date + timedelta(seconds=random_seconds)
        
        # Duration, talktime, acwtime, ansholdtime
        # Let's say talktime is between 0 and 3240 seconds
        talktime = random.randint(0, 3240)
        
        # acwtime is answered call waiting time
        acwtime = random.randint(0, 300) 
        
        # ansholdtime is hold time for answered call
        ansholdtime = random.randint(0, 600)
        
        # Duration can be the sum of these, plus ringing time etc. We'll just make it total
        duration = talktime + acwtime + ansholdtime + random.randint(5, 60)
        
        segstop = segstart + timedelta(seconds=duration)
        
        # UTC times (assuming segstart is IST (UTC+5:30) for example, we subtract 5.5 hours)
        # But we can just subtract 5:30 hours to make a UTC equivalent
        segstartutc = segstart - timedelta(hours=5, minutes=30)
        segstoputc = segstop - timedelta(hours=5, minutes=30)
        
        # split1: 811-822 (Digitech) / 911-922 (NSB)
        agency_code = random.choice(["8", "9"])
        lang_code = random.choice(LANGUAGE_CODES)
        split1 = f"{agency_code}{lang_code}"
        
        transferred = random.choice([0, 1])
        
        if transferred == 1:
            agt_released = 1
        else:
            agt_released = random.choice([0, 1])
            
        # Agency for login (56 for Digitech if split1 starts with 8, 57 for NSB if 9)
        if agency_code == "8":
            anslogin_prefix = "56"
            origlogin_prefix = "56"
        else:
            anslogin_prefix = "57"
            origlogin_prefix = "57"
            
        anslogin = f"{anslogin_prefix}{random.randint(10000, 99999)}"
        # origlogin similar to anslogin but different number from same organization
        origlogin = f"{origlogin_prefix}{random.randint(10000, 99999)}"
        
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
