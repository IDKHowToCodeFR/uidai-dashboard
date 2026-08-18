import pandas as pd
import random
import uuid
from datetime import datetime, timedelta
import os

# Ensure the unimate_data directory exists
output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'unimate_data')
os.makedirs(output_dir, exist_ok=True)

# Define constants
LANGUAGES = ["bn-in", "en-in", "gu-in", "hi-in", "kn-in", "ml-in", "mr-in", "or-in", "pa-in", "ta-in", "te-in"]
TERMINATION_TYPES = ["Disconnect", "Terminate", "Transfer"]
TERMINATION_REASONS = ["Customer Opted", "Error", "Exceed Tries", "System"]
DESCRIPTIONS = [
    "Call disconnected due to API failure on authentication.",
    "User opted to terminate the call early.",
    "System error occurred during the session.",
    "User exceeded maximum retry attempts for OTP.",
    "Call transferred to another department.",
    "Successful verification but disconnected soon after.",
    "Network failure on the user end.",
    "No input received from the user.",
    "Call disconnected by the system normally.",
    "User hung up during verification."
]
REGIONS = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", 
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", 
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", 
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", 
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Andaman and Nicobar Islands", 
    "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu", "Lakshadweep", "Delhi", 
    "Puducherry", "Ladakh", "Jammu and Kashmir"
]

def generate_sample_unimate_data(num_records):
    data = []
    
    start_date = datetime.now() - timedelta(days=30)
    
    for _ in range(num_records):
        # UCID and Session ID
        ucid = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # Call Start and End Time
        random_seconds = random.randint(0, 30 * 24 * 60 * 60)
        call_start_time = start_date + timedelta(seconds=random_seconds)
        
        # Call duration (in seconds, up to 15 minutes)
        call_duration_seconds = random.randint(10, 900)
        call_end_time = call_start_time + timedelta(seconds=call_duration_seconds)
        
        # Day of Week: 1 stands for SUNDAY in the required format.
        # Python's isoweekday() returns 1 (Monday) to 7 (Sunday). 
        # We need to map it: Sunday=1, Monday=2, ..., Saturday=7
        python_day = call_start_time.isoweekday()
        day_of_week = (python_day % 7) + 1
        
        # ANI (10 digits)
        ani = f"{random.randint(6, 9)}{random.randint(100000000, 999999999)}"
        
        # DNIS
        # 56..... for digitech, 57....... for NSB. Let's make it 7 digits total.
        agency_prefix = random.choice(["56", "57"])
        dnis = f"{agency_prefix}{random.randint(10000, 99999)}"
        
        # Language
        language = random.choice(LANGUAGES)
        
        # Authentication
        is_authenticated = random.choice([True, False])
        
        # Authentication Mechanism
        if is_authenticated:
            auth_mechanism = random.choice(["OTP", "DOB"])
        else:
            auth_mechanism = ""
            
        # Termination Type and Reason
        term_type = random.choice(TERMINATION_TYPES)
        term_reason = random.choice(TERMINATION_REASONS)
        
        # Description
        description = random.choice(DESCRIPTIONS)
        
        # Region
        region = random.choice(REGIONS)
        
        data.append({
            "UCID": ucid,
            "Session ID": session_id,
            "Day of Week": day_of_week,
            "Call Start Time": call_start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "Call End Time": call_end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "Call Duration": str(timedelta(seconds=call_duration_seconds)),
            "ANI": ani,
            "DNIS": dnis,
            "Language": language,
            "Authentication": is_authenticated,
            "Authentication Mechanism": auth_mechanism,
            "Termination Type": term_type,
            "Termination Reason": term_reason,
            "Description": description,
            "Region": region
        })
        
    df = pd.DataFrame(data)
    
    # Save to Excel
    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"unimate_data_{current_time_str}.xlsx"
    file_path = os.path.join(output_dir, file_name)
    
    df.to_excel(file_path, index=False)
    print(f"Successfully generated {num_records} sample records at {file_path}")

if __name__ == "__main__":
    n = int(input("Input rows"))
    generate_sample_unimate_data(n)
