import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta, date
import os

output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uidai_data', 'cdr_data')
os.makedirs(output_dir, exist_ok=True)

# --- Shared conventions (consistent across CDR/Unimate/CCF/APR) ---

# split1: first digit = vendor (8=Digitech, 9=NSB), last 2 digits = language code
LANGUAGE_CODES = {
    "11": "Hindi", "12": "English", "13": "Bengali", "14": "Telugu",
    "15": "Marathi", "16": "Tamil", "17": "Gujarati", "18": "Kannada",
    "19": "Odia", "20": "Malayalam", "21": "Punjabi", "22": "Assamese",
}
LANG_CODES_LIST = list(LANGUAGE_CODES.keys())
LANG_WEIGHTS = np.array([0.44, 0.18, 0.07, 0.05, 0.05, 0.05, 0.04, 0.03, 0.02, 0.02, 0.03, 0.02])
LANG_WEIGHTS /= LANG_WEIGHTS.sum()

# anslogin/origlogin: 7-digit, 56xxxxx=Digitech, 57xxxxx=NSB
# Time-of-day weights — peak 10am-2pm, realistic BPO curve
HOUR_WEIGHTS = np.array([
    0.005, 0.003, 0.002, 0.002, 0.003, 0.005,   # 00-05 (night)
    0.015, 0.025, 0.045, 0.075,                   # 06-09 (morning ramp)
    0.110, 0.120, 0.120, 0.110,                   # 10-13 (peak)
    0.090, 0.080, 0.065, 0.045,                   # 14-17 (afternoon)
    0.030, 0.020, 0.012, 0.008,                   # 18-21 (evening)
    0.005, 0.005,                                  # 22-23 (late night)
])
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()

GOVT_HOLIDAYS_2026 = {
    date(2026, 1, 26), date(2026, 3, 10), date(2026, 3, 17), date(2026, 3, 31),
    date(2026, 4, 3), date(2026, 4, 14), date(2026, 5, 1), date(2026, 6, 7),
    date(2026, 7, 6), date(2026, 8, 15), date(2026, 8, 21), date(2026, 10, 2),
    date(2026, 10, 20), date(2026, 11, 9), date(2026, 11, 11), date(2026, 12, 25),
}


def generate_sample_cdr_data(daily_calls: int = 50000, days: int = 180):
    """
    Generate CDR data: one row per call segment, streamed to CSV in daily chunks.
    50k calls/day x 180 days ≈ 9M rows. Uses numpy vectorization per-day for speed.
    """
    rng = np.random.default_rng()
    start_date = datetime.now() - timedelta(days=days)

    # Pre-generate stable agent pools (reused across days for realism)
    digitech_agents = np.array([f"56{x}" for x in random.sample(range(10000, 100000), 400)])
    nsb_agents = np.array([f"57{x}" for x in random.sample(range(10000, 100000), 260)])

    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"cdr_data_{current_time_str}.xlsx"
    file_path = os.path.join(output_dir, file_name)

    total_rows = 0
    all_chunks = []

    for day_offset in range(days):
            current = start_date + timedelta(days=day_offset)
            dow = current.weekday()  # 0=Mon, 6=Sun
            is_holiday = current.date() in GOVT_HOLIDAYS_2026

            # Daily volume: Sunday/holiday = low, Saturday = moderate
            if is_holiday:
                n = int(daily_calls * random.uniform(0.12, 0.18))
            elif dow == 6:  # Sunday
                n = int(daily_calls * random.uniform(0.20, 0.30))
            elif dow == 5:  # Saturday
                n = int(daily_calls * random.uniform(0.50, 0.60))
            else:
                n = max(1, daily_calls + rng.integers(min(-3000, -daily_calls//2), max(3000, daily_calls//2)))

            if day_offset % 30 == 0:
                print(f"  CDR: day {day_offset + 1}/{days} ({n:,} calls) ...")

            # --- Vectorized generation for this day ---

            # Call IDs: 9-digit numeric, unique within day
            call_ids = rng.integers(100_000_000, 1_000_000_000, size=n)

            # Timestamps: hour weighted by TOD curve, random minute/second
            hours = rng.choice(24, size=n, p=HOUR_WEIGHTS)
            minutes = rng.integers(0, 60, size=n)
            seconds = rng.integers(0, 60, size=n)

            # Build segstart/segstop/UTC using pandas vectorized datetime ops
            base_ts = pd.Timestamp(current.date())
            start_offsets = pd.to_timedelta(
                hours.astype(np.int64) * 3600 + minutes.astype(np.int64) * 60 + seconds.astype(np.int64), unit='s'
            )
            segstart_ts = base_ts + start_offsets

            # Talktime: lognormal, median ~90s, heavy tail up to 54 min
            talktime = np.clip(rng.lognormal(4.5, 1.2, size=n).astype(int), 0, 3240)

            # ACW (after-call work): lognormal, 10-300s
            acwtime = np.clip(rng.lognormal(3.2, 0.8, size=n).astype(int), 0, 300)

            # Hold time: 35% of calls have hold, lognormal 10-600s
            has_hold = rng.random(n) < 0.35
            hold_raw = np.clip(rng.lognormal(3.0, 1.0, size=n).astype(int), 0, 600)
            ansholdtime = np.where(has_hold, hold_raw, 0)

            # Duration = talk + acw + hold + ring overhead
            ring_overhead = rng.integers(5, 30, size=n)
            duration = talktime + acwtime + ansholdtime + ring_overhead

            segstop_ts = segstart_ts + pd.to_timedelta(duration.astype(np.int64), unit='s')
            ist_offset = pd.Timedelta(hours=5, minutes=30)
            segstartutc_ts = segstart_ts - ist_offset
            segstoputc_ts = segstop_ts - ist_offset

            # Format datetime strings
            segstart_strs = segstart_ts.strftime("%d-%m-%Y %H:%M:%S")
            segstop_strs = segstop_ts.strftime("%d-%m-%Y %H:%M:%S")
            segstartutc_strs = segstartutc_ts.strftime("%d-%m-%Y %H:%M:%S")
            segstoputc_strs = segstoputc_ts.strftime("%d-%m-%Y %H:%M:%S")

            # Vendor & language via split1
            agency_codes = rng.choice(np.array(["8", "9"]), size=n, p=[0.6, 0.4])
            lang_codes = rng.choice(np.array(LANG_CODES_LIST), size=n, p=LANG_WEIGHTS)
            split1 = np.char.add(agency_codes, lang_codes)

            # Transfer / agent release logic (format.txt rules)
            transferred = (rng.random(n) < 0.08).astype(int)
            agt_released = np.where(
                transferred == 1,
                0,  # transferred=1 → agt_released always 0
                (rng.random(n) < 0.90).astype(int)  # transferred=0 → 90% released
            )

            # Agent logins from vendor pools
            is_digitech = agency_codes == "8"
            anslogin = np.where(is_digitech, rng.choice(digitech_agents, size=n), rng.choice(nsb_agents, size=n))
            origlogin = np.where(is_digitech, rng.choice(digitech_agents, size=n), rng.choice(nsb_agents, size=n))

            chunk_df = pd.DataFrame({
                "Call Id": call_ids,
                "acwtime": acwtime,
                "ansholdtime": ansholdtime,
                "duration": duration,
                "segstart": segstart_strs,
                "segstartutc": segstartutc_strs,
                "segstop": segstop_strs,
                "segstoputc": segstoputc_strs,
                "talktime": talktime,
                "split1": split1,
                "transferred": transferred,
                "agt_released": agt_released,
                "origlogin": origlogin,
                "anslogin": anslogin,
            })

            all_chunks.append(chunk_df)
            total_rows += n

    final_df = pd.concat(all_chunks, ignore_index=True)
    final_df.to_excel(file_path, index=False)
    print(f"Generated {total_rows:,} CDR records -> {file_path}")
    print(f"  File size: {os.path.getsize(file_path) / (1024**2):.1f} MB")


if __name__ == "__main__":
    n_input = input("Daily calls (default 1000): ")
    n = int(n_input) if n_input.strip() else 1000
    days_input = input("Days (default 180): ")
    d = int(days_input) if days_input.strip() else 180
    generate_sample_cdr_data(n, d)
