import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os
import math

def generate_data():
    languages = ['Hindi', 'Bengali', 'Marathi', 'Telugu', 'Tamil', 'Gujarati', 'Urdu', 'Kannada', 'Odia', 'Malayalam', 'Punjabi', 'Assamese']
    lang_weights = [0.43, 0.08, 0.07, 0.06, 0.05, 0.05, 0.04, 0.04, 0.03, 0.03, 0.02, 0.10]
    total_w = sum(lang_weights)
    lang_weights = [w/total_w for w in lang_weights]

    start_date = datetime(2023, 7, 1)
    days_in_july = 31

    companies = [("Digitech", 0.6), ("NSB", 0.4)]
    
    out_dir = "data/unprocessed"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "july_trend_data.xlsx")
    
    # Define an hourly volume curve (0-23 hours). 
    # Low at night, peak around 10-12 and 14-16.
    hourly_curve = [
        0.05, 0.03, 0.02, 0.01, 0.02, 0.05, # 0-5
        0.15, 0.30, 0.60, 0.85, 1.00, 0.95, # 6-11
        0.80, 0.75, 0.85, 0.90, 0.70, 0.50, # 12-17
        0.40, 0.35, 0.30, 0.20, 0.15, 0.10  # 18-23
    ]
    
    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        for company, ratio in companies:
            records = []
            
            # Base call volume multiplier
            base_vol = ratio * 1500 # Scaled up for daily volume distributed across hours
            
            for d in range(days_in_july):
                current_date = start_date + timedelta(days=d)
                day_name = current_date.strftime("%A")
                
                # Daily trend factor (-1.0 to 1.0) using sine wave
                trend = math.sin(d / 31.0 * 2 * math.pi)
                
                # Weekend modifier
                is_weekend = current_date.weekday() >= 5
                vol_mod = 0.6 if is_weekend else 1.0 + (trend * 0.2)
                
                for hour in range(24):
                    hour_vol_curve = hourly_curve[hour]
                    
                    for idx, lang in enumerate(languages):
                        lang_weight = lang_weights[idx]
                        
                        # Expected volume for this hour, company, and language
                        expected_vol = base_vol * vol_mod * hour_vol_curve * lang_weight
                        
                        if expected_vol < 1:
                            # small chance to have 1 or 2 calls for tiny queues at night
                            if random.random() > 0.1:
                                continue
                            expected_vol = random.uniform(1, 3)
                        
                        # Add variance
                        actual_vol = int(np.random.normal(expected_vol, expected_vol * 0.2))
                        if actual_vol <= 0: continue
                        
                        # High volume (peak hours) reduces Service Level and increases Abandons
                        peak_penalty = hour_vol_curve * random.uniform(0.05, 0.15)
                        
                        aban_rate = random.uniform(0.02, 0.08) + peak_penalty
                        aban_calls = int(actual_vol * aban_rate)
                        acd_calls = actual_vol - aban_calls
                        if acd_calls <= 0: acd_calls = 0
                        
                        call_offered = acd_calls + aban_calls
                        if call_offered == 0: continue
                        
                        aban_10s = int(aban_calls * random.uniform(0.4, 0.8))
                        
                        sl_target = random.uniform(0.85, 0.98) - peak_penalty - (trend * 0.05)
                        sl_target = max(min(sl_target, 1.0), 0.3)
                        
                        denom = call_offered - aban_10s
                        acd_20s = int(denom * sl_target)
                        if acd_20s < 0: acd_20s = 0
                        if acd_20s > acd_calls: acd_20s = acd_calls
                        
                        acd_10s = int(acd_20s * random.uniform(0.6, 0.9))
                        
                        # Target AHT varies by hour (longer at night or peak)
                        target_aht = 220 + (peak_penalty * 300) + random.uniform(-20, 40)
                        target_aht = max(target_aht, 120)
                        
                        acd_time = int(acd_calls * (target_aht * random.uniform(0.70, 0.80)))
                        acw_time = int(acd_calls * (target_aht * random.uniform(0.10, 0.20)))
                        hold_time = int(acd_calls * (target_aht * random.uniform(0.05, 0.15)))
                        
                        held_calls = int(acd_calls * random.uniform(0.1, 0.4))

                        records.append({
                            "Date": current_date.strftime("%Y-%m-%d"),
                            "Hour": hour,
                            "Day": day_name,
                            "Language": lang,
                            "ACD Calls in 10 Sec": acd_10s,
                            "ACD Calls in 20 Sec": acd_20s,
                            "ABAN Calls in 10 Sec": aban_10s,
                            "Call Offered": call_offered,
                            "ACD Calls": acd_calls,
                            "ABAN Calls": aban_calls,
                            "ACD Time": acd_time,
                            "ACW Time": acw_time,
                            "Hold Time": hold_time,
                            "Held Calls": held_calls
                        })
                        
            df = pd.DataFrame(records)
            df.to_excel(writer, sheet_name=company, index=False)
            print(f"Generated {len(df)} rows for {company}")

if __name__ == "__main__":
    generate_data()
