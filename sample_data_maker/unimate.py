import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta, date
import os

output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uidai_data', 'unimate_data')
os.makedirs(output_dir, exist_ok=True)

# --- Shared conventions (consistent across CDR/Unimate/CCF/APR) ---

LANGUAGES = ["bn-in", "en-in", "gu-in", "hi-in", "kn-in", "ml-in", "mr-in", "or-in", "pa-in", "ta-in", "te-in", "as-in"]
LANG_WEIGHTS = np.array([0.06, 0.20, 0.04, 0.44, 0.03, 0.02, 0.05, 0.02, 0.03, 0.05, 0.04, 0.02])
LANG_WEIGHTS /= LANG_WEIGHTS.sum()

TERMINATION_TYPES = ["Disconnect", "HangUp", "Transfer"]
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

# Region codes per format.txt
REGIONS = [
    "AP", "AR", "AS", "BR", "CT", "GA", "GJ", "HR", "HP", "JH", "KA",
    "KL", "MP", "MH", "MN", "ML", "MZ", "NL", "OR", "PB", "RJ", "SK",
    "TN", "TG", "TR", "UP", "UPW", "UPE", "UT", "WB", "AN", "CH",
    "DD", "LD", "DL", "PY", "LA", "JK"
]

LANG_TO_REGIONS = {
    "bn-in": ["WB", "TR"],
    "en-in": ["DL", "MH", "KA", "TN", "TG"],
    "gu-in": ["GJ", "DD"],
    "hi-in": ["UP", "UPW", "UPE", "BR", "MP", "RJ", "HR", "DL", "JH", "CT", "UT", "HP"],
    "kn-in": ["KA"],
    "ml-in": ["KL", "LD"],
    "mr-in": ["MH", "GA"],
    "or-in": ["OR"],
    "pa-in": ["PB", "CH"],
    "ta-in": ["TN", "PY"],
    "te-in": ["AP", "TG"],
    "as-in": ["AS"]
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

def generate_sample_unimate_data(daily_calls: int = 50000, days: int = 180):
    """
    Generate Unimate data: one row per case, streamed to CSV in daily chunks.
    50k calls/day x 180 days ≈ 9M rows. Vectorized for speed.
    """
    rng = np.random.default_rng()
    start_date = datetime.now() - timedelta(days=days)

    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"unimate_data_{current_time_str}.xlsx"
    file_path = os.path.join(output_dir, file_name)

    total_rows = 0
    all_chunks = []

    for day_offset in range(days):
            current = start_date + timedelta(days=day_offset)
            dow = current.weekday()
            is_holiday = current.date() in GOVT_HOLIDAYS_2026

            if is_holiday:
                n = int(daily_calls * random.uniform(0.12, 0.18))
            elif dow == 6:
                n = int(daily_calls * random.uniform(0.20, 0.30))
            elif dow == 5:
                n = int(daily_calls * random.uniform(0.50, 0.60))
            else:
                n = max(1, daily_calls + rng.integers(min(-3000, -daily_calls//2), max(3000, daily_calls//2)))

            if day_offset % 30 == 0:
                print(f"  Unimate: day {day_offset + 1}/{days} ({n:,} calls) ...")

            # UCID / Session ID: 10-digit numeric
            ucids = rng.integers(1_000_000_000, 10_000_000_000, size=n)
            session_ids = rng.integers(1_000_000_000, 10_000_000_000, size=n)

            hours = rng.choice(24, size=n, p=HOUR_WEIGHTS)
            minutes = rng.integers(0, 60, size=n)
            seconds = rng.integers(0, 60, size=n)

            base_ts = pd.Timestamp(current.date())
            start_offsets = pd.to_timedelta(
                hours.astype(np.int64) * 3600 + minutes.astype(np.int64) * 60 + seconds.astype(np.int64), unit='s'
            )
            call_start_ts = base_ts + start_offsets

            # Duration up to 15 mins (mostly shorter)
            call_duration_seconds = np.clip(rng.lognormal(4.5, 1.2, size=n).astype(int), 10, 900)
            call_end_ts = call_start_ts + pd.to_timedelta(call_duration_seconds.astype(np.int64), unit='s')

            day_of_week = ((dow + 1) % 7) + 1 # 1 for SUNDAY

            # ANI (10 digits starting with 6-9)
            ani = rng.integers(6, 10, size=n).astype(str)
            ani = np.char.add(ani, rng.integers(100_000_000, 1_000_000_000, size=n).astype(str))

            # DNIS: 56xxxxx (Digitech) or 57xxxxx (NSB) (Matches backend parsing rules & 60/40 ratio)
            agency_prefix = rng.choice(["56", "57"], size=n, p=[0.6, 0.4])
            dnis_suffix = rng.integers(10000, 100000, size=n).astype(str)
            dnis = np.char.add(agency_prefix, dnis_suffix)

            language = rng.choice(LANGUAGES, size=n, p=LANG_WEIGHTS)
            
            # Skewed Auth Rates (85% True, 15% False)
            is_authenticated = rng.choice([True, False], size=n, p=[0.85, 0.15])
            
            # Skewed Mech (90% OTP, 10% DOB)
            auth_mech = np.where(is_authenticated, rng.choice(["OTP", "DOB"], size=n, p=[0.90, 0.10]), "")

            # Skewed Terminations
            term_type = rng.choice(TERMINATION_TYPES, size=n, p=[0.65, 0.25, 0.10])
            term_reason = rng.choice(TERMINATION_REASONS, size=n, p=[0.75, 0.05, 0.05, 0.15])
            description = rng.choice(DESCRIPTIONS, size=n)

            # Map region based on language, fallback to random region
            regions = np.empty(n, dtype=object)
            for lang_key, region_list in LANG_TO_REGIONS.items():
                mask = language == lang_key
                if np.any(mask):
                    regions[mask] = rng.choice(region_list, size=np.sum(mask))
            
            # For any missing/unmapped, just random region
            missing_mask = pd.isna(regions)
            if np.any(missing_mask):
                regions[missing_mask] = rng.choice(REGIONS, size=np.sum(missing_mask))

            call_start_strs = call_start_ts.strftime("%Y-%m-%d %H:%M:%S")
            call_end_strs = call_end_ts.strftime("%Y-%m-%d %H:%M:%S")

            # Duration formatted as HH:MM:SS string
            def format_duration(seconds):
                h = seconds // 3600
                m = (seconds % 3600) // 60
                s = seconds % 60
                # Vectorized operations on string arrays can be tricky, easier to just use pd mapping
                return pd.Series(seconds).apply(lambda x: f"{x//3600:02d}:{(x%3600)//60:02d}:{x%60:02d}").values
            
            duration_strs = format_duration(call_duration_seconds)

            chunk_df = pd.DataFrame({
                "UCID": ucids,
                "Session ID": session_ids,
                "Day of Week": np.full(n, day_of_week),
                "Call Start Time": call_start_strs,
                "Call End Time": call_end_strs,
                "Call Duration": duration_strs,
                "ANI": ani,
                "DNIS": dnis,
                "Language": language,
                "Authentication": is_authenticated,
                "Authentication Mechanism": auth_mech,
                "Termination Type": term_type,
                "Termination Reason": term_reason,
                "Description": description,
                "Region": regions
            })

            all_chunks.append(chunk_df)
            total_rows += n

    final_df = pd.concat(all_chunks, ignore_index=True)
    final_df.to_excel(file_path, index=False)
    print(f"Generated {total_rows:,} Unimate records -> {file_path}")
    print(f"  File size: {os.path.getsize(file_path) / (1024**2):.1f} MB")

if __name__ == "__main__":
    n_input = input("Daily calls (default 1000): ")
    n = int(n_input) if n_input.strip() else 1000
    days_input = input("Days (default 180): ")
    d = int(days_input) if days_input.strip() else 180
    generate_sample_unimate_data(n, d)
