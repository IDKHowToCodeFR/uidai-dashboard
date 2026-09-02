import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta, date
import os
import itertools

# Ensure the uidai_data/ccf_data directory exists
output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uidai_data', 'ccf_data')
os.makedirs(output_dir, exist_ok=True)

# Define constants
VENDORS = {"Digitech": 0.6, "NSB": 0.4}
LANGUAGES = [
    "Hindi", "English", "Kannada", "Assamese", "Bengali", "Punjabi", 
    "Marathi", "Gujarati", "Odia", "Tamil", "Telugu", "Malayalam"
]

LANG_WEIGHTS_DICT = {
    "Hindi": 0.44, "English": 0.18, "Bengali": 0.07, "Telugu": 0.05, 
    "Marathi": 0.05, "Tamil": 0.05, "Gujarati": 0.04, "Kannada": 0.03, 
    "Odia": 0.02, "Malayalam": 0.02, "Punjabi": 0.03, "Assamese": 0.02
}

HOUR_WEIGHTS = np.array([
    0.005, 0.003, 0.002, 0.002, 0.003, 0.005,   # 00-05
    0.015, 0.025, 0.045, 0.075,                   # 06-09
    0.110, 0.120, 0.120, 0.110,                   # 10-13
    0.090, 0.080, 0.065, 0.045,                   # 14-17
    0.030, 0.020, 0.012, 0.008,                   # 18-21
    0.005, 0.005,                                  # 22-23
])
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()

GOVT_HOLIDAYS_2026 = {
    date(2026, 1, 26), date(2026, 3, 10), date(2026, 3, 17), date(2026, 3, 31),
    date(2026, 4, 3), date(2026, 4, 14), date(2026, 5, 1), date(2026, 6, 7),
    date(2026, 7, 6), date(2026, 8, 15), date(2026, 8, 21), date(2026, 10, 2),
    date(2026, 10, 20), date(2026, 11, 9), date(2026, 11, 11), date(2026, 12, 25),
}

def generate_sample_ccf_data(daily_calls: int = 50000, days: int = 180):
    rng = np.random.default_rng()
    start_date = datetime.now() - timedelta(days=days)
    
    # We will generate a complete grid of 15-minute intervals for all vendors and languages
    # 96 intervals/day
    intervals_per_day = 96
    
    # Pre-calculate hour of day for each interval (0 to 95) -> 0 to 23
    interval_hours = np.repeat(np.arange(24), 4)
    # The weight for each interval is simply the hour weight / 4
    interval_weights = HOUR_WEIGHTS[interval_hours] / 4.0
    
    all_data = []

    for day_offset in range(days):
        current_date = start_date + timedelta(days=day_offset)
        dow = current_date.weekday()
        is_holiday = current_date.date() in GOVT_HOLIDAYS_2026
        
        if is_holiday:
            daily_total = int(daily_calls * random.uniform(0.12, 0.18))
        elif dow == 6:
            daily_total = int(daily_calls * random.uniform(0.20, 0.30))
        elif dow == 5:
            daily_total = int(daily_calls * random.uniform(0.50, 0.60))
        else:
            daily_total = max(1, daily_calls + rng.integers(min(-3000, -daily_calls//2), max(3000, daily_calls//2)))

        if day_offset % 30 == 0:
            print(f"  CCF: generating day {day_offset + 1}/{days} ({daily_total:,} calls)...")

        base_ts = pd.Timestamp(current_date.date())
        date_str = current_date.strftime("%Y-%m-%d")
        day_name = current_date.strftime("%A")

        # For each interval, vendor, and language, distribute the daily_total
        # This is a multinomial distribution.
        
        # Grid dimensions: 96 intervals x 2 vendors x 12 languages = 2304 combinations
        # We need the probability of each combination.
        # Prob = interval_weight * vendor_weight * lang_weight
        
        flat_probs = []
        combos = []
        
        for i in range(96):
            i_weight = interval_weights[i]
            ts = base_ts + pd.to_timedelta(i * 15, unit='min')
            ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
            for vendor, v_weight in VENDORS.items():
                for lang in LANGUAGES:
                    l_weight = LANG_WEIGHTS_DICT[lang]
                    p = i_weight * v_weight * l_weight
                    flat_probs.append(p)
                    combos.append({
                        "Call Timestamp": ts_str,
                        "Date": date_str,
                        "Day": day_name,
                        "Vendor": vendor,
                        "Language": lang
                    })
                    
        flat_probs = np.array(flat_probs)
        flat_probs /= flat_probs.sum()
        
        # Generate exact call counts for each combination
        call_counts = rng.multinomial(daily_total, flat_probs)
        
        # Process the combinations
        for idx, count in enumerate(call_counts):
            if count == 0:
                continue
                
            combo = combos[idx]
            call_offered = count
            
            # Typical abandonment rate ~5-8%
            aban_calls = int(call_offered * rng.uniform(0.02, 0.10))
            acd_calls = call_offered - aban_calls
            
            # Sub-metrics
            acd_10 = int(acd_calls * rng.uniform(0.4, 0.7)) if acd_calls > 0 else 0
            acd_20 = int(acd_10 + (acd_calls - acd_10) * rng.uniform(0.5, 0.9)) if acd_calls > 0 else 0
            aban_10 = int(aban_calls * rng.uniform(0.1, 0.4)) if aban_calls > 0 else 0
            
            # Times (in seconds, matches raw data structure logic)
            acd_time = int(acd_calls * rng.uniform(120, 240))
            acw_time = int(acd_calls * rng.uniform(15, 60))
            hold_time = int(acd_calls * rng.uniform(10, 45) * 0.35) # 35% have hold time
            held_calls = int(acd_calls * rng.uniform(0.2, 0.5)) if acd_calls > 0 else 0
            
            combo.update({
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
            all_data.append(combo)

    df = pd.DataFrame(all_data)
    
    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"ccf_skill_data_{current_time_str}.xlsx"
    file_path = os.path.join(output_dir, file_name)
    
    with pd.ExcelWriter(file_path) as writer:
        for vendor_name in VENDORS.keys():
            vendor_df = df[df["Vendor"] == vendor_name].copy()
            vendor_df = vendor_df.drop(columns=["Vendor"])
            vendor_df.to_excel(writer, sheet_name=vendor_name, index=False)
            
    print(f"Successfully generated CCF sample records (180 days grid) at {file_path}")

if __name__ == "__main__":
    n_input = input("Daily calls (default 50000): ")
    n = int(n_input) if n_input.strip() else 50000
    days_input = input("Days (default 180): ")
    d = int(days_input) if days_input.strip() else 180
    generate_sample_ccf_data(n, d)
