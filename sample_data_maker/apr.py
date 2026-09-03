import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta, date
import os

output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'uidai_data', 'apr_data')
os.makedirs(output_dir, exist_ok=True)

# --- Shared conventions (consistent across CDR/Unimate/CCF/APR) ---

VENDORS = {
    "Digitech": {"prefix": "56", "weight": 0.6, "skill_prefix": "DIGI"},
    "NSB":      {"prefix": "57", "weight": 0.4, "skill_prefix": "NSB"},
}

LANGUAGES = [
    "Hindi", "English", "Bengali", "Telugu", "Marathi", "Tamil",
    "Gujarati", "Kannada", "Odia", "Malayalam", "Punjabi", "Assamese"
]
LANG_WEIGHTS = [0.44, 0.18, 0.07, 0.05, 0.05, 0.05, 0.04, 0.03, 0.02, 0.02, 0.03, 0.02]

# Major Indian government holidays (2026) — same list across all generators
GOVT_HOLIDAYS_2026 = {
    date(2026, 1, 26), date(2026, 3, 10), date(2026, 3, 17), date(2026, 3, 31),
    date(2026, 4, 3), date(2026, 4, 14), date(2026, 5, 1), date(2026, 6, 7),
    date(2026, 7, 6), date(2026, 8, 15), date(2026, 8, 21), date(2026, 10, 2),
    date(2026, 10, 20), date(2026, 11, 9), date(2026, 11, 11), date(2026, 12, 25),
}

FIRST_NAMES = [
    "Aarav", "Aditi", "Amit", "Ananya", "Arjun", "Deepa", "Gaurav", "Ishita",
    "Kavita", "Manish", "Neha", "Priya", "Rahul", "Ravi", "Rohit", "Sakshi",
    "Sneha", "Suresh", "Tanvi", "Vikram", "Pooja", "Harsh", "Divya", "Kiran",
    "Meera", "Nikhil", "Pallavi", "Rajesh", "Sanjay", "Shreya", "Tushar",
    "Varun", "Yogesh", "Zara", "Bhavna", "Chetan", "Disha", "Esha", "Farhan",
    "Geeta", "Hemant", "Isha", "Jayesh", "Komal", "Lakshmi", "Mohan", "Nidhi",
    "Om", "Pankaj", "Rekha", "Shubham", "Aishwarya", "Akash", "Bharat", "Chandni",
    "Devendra", "Ekta", "Faisal", "Govind", "Hema", "Irfan", "Jyoti", "Kartik",
    "Lalita", "Mahesh", "Namita", "Omkar", "Preeti", "Raghav", "Savita", "Tarun",
    "Uma", "Vivek", "Wajid", "Yashika", "Zubaida",
]
LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Singh", "Kumar", "Gupta", "Reddy", "Nair",
    "Das", "Joshi", "Mehta", "Shah", "Rao", "Iyer", "Pillai", "Bhat",
    "Chauhan", "Yadav", "Mishra", "Pandey", "Desai", "Kulkarni", "Shetty",
    "Menon", "Chopra", "Malhotra", "Banerjee", "Mukherjee", "Ghosh", "Bose",
    "Tiwari", "Dubey", "Saxena", "Agarwal", "Kapoor", "Thakur", "Rathore",
    "Bhatt", "Naik", "Patil", "Deshpande", "Hegde", "Kaur", "Gill", "Sethi",
    "Bhatia", "Arora", "Srivastava", "Trivedi", "Vyas",
]


def _fmt_hms(total_seconds: int) -> str:
    """Format seconds as HH:MM:SS."""
    total_seconds = max(0, int(total_seconds))
    h = total_seconds // 3600
    m = (total_seconds % 3600) // 60
    s = total_seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def generate_sample_apr_data(num_agents: int = 600, days: int = 180):
    """
    Generate APR data: one row per agent per working day.
    ~600 agents (360 Digitech + 240 NSB), 180 days ≈ ~92K rows.
    """
    data = []
    start_date = datetime.now() - timedelta(days=days)

    # --- Build stable agent roster ---
    agents = []
    for vendor_name, vinfo in VENDORS.items():
        count = int(num_agents * vinfo["weight"])
        used_logins = set()
        for _ in range(count):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            agent_name = f"{vendor_name}_{first} {last}"
            # 7-digit login: prefix + 5 random digits
            while True:
                login_id = f"{vinfo['prefix']}{random.randint(10000, 99999)}"
                if login_id not in used_logins:
                    used_logins.add(login_id)
                    break
            lang = random.choices(LANGUAGES, weights=LANG_WEIGHTS, k=1)[0]
            skill = f"{vinfo['skill_prefix']}_{lang}"
            agents.append({
                "name": agent_name, "login": login_id,
                "vendor": vendor_name, "lang": lang, "skill": skill,
            })

    print(f"  APR: built roster of {len(agents)} agents")

    for day_offset in range(days):
        current = start_date + timedelta(days=day_offset)
        day_name = current.strftime("%A")
        is_sunday = day_name == "Sunday"
        is_saturday = day_name == "Saturday"
        is_holiday = current.date() in GOVT_HOLIDAYS_2026

        if day_offset % 30 == 0:
            print(f"  APR: generating day {day_offset + 1}/{days} ...")

        for agent in agents:
            # Realistic absence rates
            if is_holiday and random.random() < 0.60:
                continue
            if is_sunday and random.random() < 0.70:
                continue
            if is_saturday and random.random() < 0.40:
                continue
            if not is_sunday and not is_saturday and not is_holiday and random.random() < 0.15:
                continue

            # --- Core ACD metrics ---
            if is_holiday:
                acd_calls = int(np.clip(np.random.normal(30, 10), 0, None))
            elif is_sunday:
                acd_calls = int(np.clip(np.random.normal(25, 8), 0, None))
            elif is_saturday:
                acd_calls = int(np.clip(np.random.normal(45, 12), 0, None))
            else:
                acd_calls = int(np.clip(np.random.normal(90, 25), 0, None))

            # Skewed (Lognormal) handle times
            avg_acd_time = int(np.clip(np.random.lognormal(5.4, 0.4), 60, 600))
            avg_acw_time = int(np.clip(np.random.lognormal(3.4, 0.5), 10, 180))

            acd_time_sec = acd_calls * avg_acd_time
            acw_time_sec = acd_calls * avg_acw_time
            ring_time_sec = acd_calls * int(np.clip(np.random.lognormal(1.8, 0.3), 3, 20))

            # Staffed time: normally ~8.5 hours
            staffed_time_sec = int(np.clip(np.random.normal(30600, 1800), 18000, 36000))

            # Break times (skewed normal)
            tea_sec = int(np.clip(np.random.normal(900, 180), 300, 1800))
            lunch_sec = int(np.clip(np.random.normal(2700, 600), 1800, 3600))
            quality_sec = int(np.clip(np.random.exponential(300), 0, 1800))
            email_sec = int(np.clip(np.random.exponential(150), 0, 1200))
            briefing_sec = int(np.clip(np.random.normal(600, 120), 0, 1800))
            sysdown_sec = int(np.clip(np.random.exponential(200), 0, 3600))
            meeting_sec = int(np.clip(np.random.exponential(400), 0, 3600))

            total_breaks = tea_sec + lunch_sec + quality_sec + email_sec + briefing_sec + sysdown_sec + meeting_sec
            aux_time_sec = total_breaks
            avail_time_sec = max(0, staffed_time_sec - total_breaks)
            productive = acd_time_sec + acw_time_sec + ring_time_sec
            other_time_sec = max(0, staffed_time_sec - productive - total_breaks)

            # Occupancy percentages
            if avail_time_sec > 0:
                occ_with = min(99.9, (productive / avail_time_sec) * 100)
                occ_without = min(occ_with, ((acd_time_sec + ring_time_sec) / avail_time_sec) * 100)
            else:
                occ_with = occ_without = 0.0

            # Held time, transfer, conference
            held_count = random.randint(0, int(acd_calls * 0.35))
            held_time_sec = held_count * random.randint(10, 30)
            trans_out = random.randint(0, max(1, int(acd_calls * 0.08)))
            conf = random.randint(0, max(1, int(acd_calls * 0.02)))

            data.append({
                "Date": current.strftime("%Y-%m-%d"),
                "Agent Name": agent["name"],
                "Login ID": agent["login"],
                "ACD Calls": acd_calls,
                "Avg ACD Time": avg_acd_time,
                "Avg ACW Time": avg_acw_time,
                "% Agent Occupancy with ACW": round(occ_with, 2),
                "% Agent Occupancy without ACW": round(occ_without, 2),
                "ACD Time": _fmt_hms(acd_time_sec),
                "ACW Time": _fmt_hms(acw_time_sec),
                "Agent Ring Time": _fmt_hms(ring_time_sec),
                "Other Time": _fmt_hms(other_time_sec),
                "AUX Time": _fmt_hms(aux_time_sec),
                "Avail Time": _fmt_hms(avail_time_sec),
                "Staffed Time": _fmt_hms(staffed_time_sec),
                "Held Calls": _fmt_hms(held_time_sec),
                "Tea Break": _fmt_hms(tea_sec),
                "Lunch / Dinner": _fmt_hms(lunch_sec),
                "Quality Feedback": _fmt_hms(quality_sec),
                "Email Support": _fmt_hms(email_sec),
                "Briefing": _fmt_hms(briefing_sec),
                "System Down": _fmt_hms(sysdown_sec),
                "Meeting": _fmt_hms(meeting_sec),
                "Trans Out": trans_out,
                "Split / Skill": agent["skill"],
                "Conf": conf,
            })

    df = pd.DataFrame(data)
    df = df.sort_values(by=["Date", "Agent Name"])

    current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"apr_data_{current_time_str}.xlsx"
    file_path = os.path.join(output_dir, file_name)
    df.to_excel(file_path, index=False)
    print(f"Generated {len(data)} APR records ({len(agents)} agents x {days} days) -> {file_path}")


if __name__ == "__main__":
    n_input = input("Agents (default 600): ")
    n = int(n_input) if n_input.strip() else 600
    days_input = input("Days (default 180): ")
    d = int(days_input) if days_input.strip() else 180
    generate_sample_apr_data(n, d)
