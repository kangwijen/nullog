import os
import pickle
from datetime import datetime
from constants import COOKIES_DIR, COOKIES_FILE, DEFAULT_USER_AGENT

def get_cookies_path():
    cookies_dir = os.path.join(os.path.dirname(__file__), COOKIES_DIR)
    os.makedirs(cookies_dir, exist_ok=True)
    return os.path.join(cookies_dir, COOKIES_FILE)

def save_data_to_pickle(data):
    cookies_path = get_cookies_path()
    with open(cookies_path, "wb") as f:
        pickle.dump(data, f)
    print(f"Data saved to {cookies_path}")

def load_data_from_pickle():
    cookies_path = get_cookies_path()
    if os.path.exists(cookies_path):
        with open(cookies_path, "rb") as f:
            return pickle.load(f)
    return None

def is_valid_time_format(time_str):
    if time_str == "OFF":
        return True
    
    if (len(time_str) == 5 and time_str[2] == ':' and 
            time_str[:2].isdigit() and time_str[3:].isdigit() and
            0 <= int(time_str[:2]) <= 23 and 0 <= int(time_str[3:]) <= 59):
        return True
    
    return False

def convert_12hour(time_str):
    if time_str == "OFF":
        return "OFF"
    
    hour, minute = map(int, time_str.split(':'))
    
    period = "am" if hour < 12 else "pm"
    
    if hour == 0:
        hour = 12
    elif hour > 12:
        hour -= 12
    
    return f"{hour:02d}:{minute:02d} {period}"

def format_iso_date(date_obj):
    if isinstance(date_obj, str):
        date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
    
    return f"{date_obj.strftime('%Y-%m-%d')}T00:00:00"
