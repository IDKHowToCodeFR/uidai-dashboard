import pandas as pd
import random
from datetime import datetime, timedelta
import os

# Ensure the ccf_data directory exists
output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ccf_data')
os.makedirs(output_dir, exist_ok=True)

# Define constants
VENDORS = ["Digitech", "NSB"]
LANGUAGES = [
    "Hindi", "English", "Kannada", "Assamese", "Bengali", "Punjabi", 
    "Marathi", "Gujrati", "Odia", "Tamil", "Telegu", "Malyalam"
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
        lang = random.choice(LANGUAGES)
        
        # Per row values based on proportional monthly distribution
        # Assuming ~30 ACD calls per 15-min interval per language
        acd_calls = random.randint(0, 50)
        aban_calls = random.randint(0, 15)
        
        acd_10 = random.randint(0, int(acd_calls * 0.5)) if acd_calls > 0 else 0
        acd_20 = random.randint(acd_10, int(acd_calls * 0.8)) if acd_calls > 0 else 0
        aban_10 = random.randint(0, aban_calls) if aban_calls > 0 else 0
        
        call_offered = acd_calls + aban_calls
        
        # Time values per interval per language
        acd_time = random.randint(0, 4) # approx hours per row
        acw_time = random.randint(0, 1) # approx hours per row
        hold_time = random.randint(0, 1) # approx hours per row
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
