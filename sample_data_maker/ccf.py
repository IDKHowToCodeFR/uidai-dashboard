import pandas as pd
import random
from datetime import datetime, timedelta
import os

# Ensure the uidai_data/ccf_data directory exists
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uidai_data', 'ccf_data')
os.makedirs(output_dir, exist_ok=True)

# Define constants
VENDORS = ["Digitech", "NSB"]
LANGUAGES = [
    "Hindi", "English", "Kannada", "Assamese", "Bengali", "Punjabi", 
    "Marathi", "Gujarati", "Odia", "Tamil", "Telugu", "Malayalam"
]

def generate_sample_ccf_data(num_records):
    data = []
    
    start_date = datetime.now() - timedelta(days=30)
    
    for _ in range(num_records):
        # Generate random 15-minute interval timestamp
        random_seconds = random.randint(0, 30 * 24 * 60 * 60)
        # Round to nearest 15 minutes (900 seconds)
        random_seconds = (random_seconds // 900) * 900
        call_timestamp = start_date + timedelta(seconds=random_seconds)
        
        date_str = call_timestamp.strftime("%Y-%m-%d")
        day_name = call_timestamp.strftime("%A")
        vendor = random.choices(VENDORS, weights=[0.6, 0.4], k=1)[0]
        # Weighted random choice for languages to match observed distribution more naturally
        lang = random.choices(LANGUAGES, weights=[0.11, 0.08, 0.08, 0.09, 0.09, 0.06, 0.09, 0.08, 0.07, 0.08, 0.09, 0.08], k=1)[0]
        
        # Per row values based on proportional monthly distribution
        # Assuming ~30 ACD calls per 15-min interval per language
        acd_calls = random.randint(0, 50)
        aban_calls = random.randint(0, 15)
        
        acd_10 = random.randint(0, int(acd_calls * 0.5)) if acd_calls > 0 else 0
        acd_20 = random.randint(acd_10, int(acd_calls * 0.8)) if acd_calls > 0 else 0
        aban_10 = random.randint(0, aban_calls) if aban_calls > 0 else 0
        
        call_offered = acd_calls + aban_calls
        
        # Time values per interval per language (cumulative seconds)
        # Naturality observation: ACD Time ~1389 mean, ACW ~341 mean, Hold ~207 mean
        acd_time = random.randint(0, acd_calls * 300) # up to 5 mins per call
        acw_time = random.randint(0, acd_calls * 60)  # up to 1 min per call
        hold_time = random.randint(0, acd_calls * 45) # up to 45 seconds per call
        held_calls = random.randint(0, acd_calls) if acd_calls > 0 else 0
        
        data.append({
            "Call Timestamp": call_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "Date": date_str,
            "Day": day_name,
            "Vendor": vendor,
            "Language": lang,
            "ACD Calls in 10 Sec": acd_10,
            "ACD Calls in 20 Sec": acd_20,
            "ABAN Calls in 10 Sec": aban_10,
            "Call Offered": call_offered,
            "ACD Calls": acd_calls,
            "ABAN Calls": aban_calls,
            "ACD Time": acd_time,
            "ACW Time": acw_time,
            "Hold Time": hold_time,
            "Held Calls": held_calls
        })
                
    df = pd.DataFrame(data)
    
    # Sort by timestamp
    df = df.sort_values(by=["Call Timestamp", "Language"])
    
    # Save to Excel
    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"ccf_skill_data_{current_time_str}.xlsx"
    file_path = os.path.join(output_dir, file_name)
    
    with pd.ExcelWriter(file_path) as writer:
        for vendor_name in VENDORS:
            vendor_df = df[df["Vendor"] == vendor_name].copy()
            vendor_df = vendor_df.drop(columns=["Vendor"])
            vendor_df.to_excel(writer, sheet_name=vendor_name, index=False)
            
    print(f"Successfully generated {num_records} CCF sample records at {file_path}")

if __name__ == "__main__":
    n = int(input("Input rows : "))
    generate_sample_ccf_data(n)
