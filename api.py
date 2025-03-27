import requests
from cookies import load_cookies
import json
from datetime import datetime

def get_logbook_months(logbook_id=""):
    cookies_data = load_cookies()
    if not cookies_data:
        raise ValueError("No cookies available. Please login first.")
    
    cookies = {cookie['name']: cookie['value'] for cookie in cookies_data}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://activity-enrichment.apps.binus.ac.id/LearningPlan/StudentIndex'
    }
    
    url = f"https://activity-enrichment.apps.binus.ac.id/LogBook/GetMonths?logBookId={logbook_id}"
    response = requests.get(url, cookies=cookies, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            month_mapping = {item['monthInt']: item['logBookHeaderID'] for item in data['data']}
            return month_mapping
        else:
            raise ValueError(f"Unexpected response format: {data}")
    else:
        raise ValueError(f"API request failed with status code {response.status_code}")

def get_logbook_entries(logbook_header_id):
    cookies_data = load_cookies()
    if not cookies_data:
        raise ValueError("No cookies available. Please login first.")
    
    cookies = {cookie['name']: cookie['value'] for cookie in cookies_data}
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://activity-enrichment.apps.binus.ac.id',
        'Referer': 'https://activity-enrichment.apps.binus.ac.id/LearningPlan/StudentIndex'
    }
    
    payload = {
        'logBookHeaderID': logbook_header_id
    }
    
    url = "https://activity-enrichment.apps.binus.ac.id/LogBook/GetLogBook"
    response = requests.post(url, data=payload, cookies=cookies, headers=headers)
    
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"error": "Failed to parse response", "raw": response.text}
    else:
        return {
            "error": f"Request failed with status code {response.status_code}",
            "raw": response.text
        }

def is_date_filled(entries_data, target_date):
    if not entries_data or "data" not in entries_data:
        return False
    
    date_str = f"{target_date}T00:00:00"
    
    for entry in entries_data["data"]:
        if entry["date"] == date_str:
            if entry["id"] != "00000000-0000-0000-0000-000000000000" and entry["clockIn"]:
                return True
    
    return False

def submit_logbook(date, activity, clock_in, clock_out, description):
    if isinstance(date, str):
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        date_str = f"{date}T00:00:00"
    elif isinstance(date, datetime):
        date_obj = date
        date_str = f"{date.strftime('%Y-%m-%d')}T00:00:00"
    else:
        raise ValueError("Date must be a string in YYYY-MM-DD format or a datetime object")
    
    month = date_obj.month
    
    cookies_data = load_cookies()
    if not cookies_data:
        raise ValueError("No cookies available. Please login first.")
    
    cookies = {cookie['name']: cookie['value'] for cookie in cookies_data}
    
    month_mapping = get_logbook_months()
    if month in month_mapping:
        logbook_header_id = month_mapping[month]
        print(f"Using LogBookHeaderID {logbook_header_id} for month {month}")
    else:
        raise ValueError(f"No LogBookHeaderID found for month {month}. Cannot proceed.")
    
    entries_data = get_logbook_entries(logbook_header_id)
    if is_date_filled(entries_data, date_obj.strftime('%Y-%m-%d')):
        raise ValueError(f"Logbook entry for date {date_obj.strftime('%Y-%m-%d')} is already filled.")

    payload = {
        "model[ID]": "00000000-0000-0000-0000-000000000000",
        "model[LogBookHeaderID]": logbook_header_id,
        "model[Date]": date_str,
        "model[Activity]": activity,
        "model[ClockIn]": clock_in,
        "model[ClockOut]": clock_out,
        "model[Description]": description,
        "model[flagjulyactive]": "false"
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Origin': 'https://activity-enrichment.apps.binus.ac.id',
        'Referer': 'https://activity-enrichment.apps.binus.ac.id/LearningPlan/StudentIndex'
    }
    
    url = "https://activity-enrichment.apps.binus.ac.id/LogBook/StudentSave"
    response = requests.post(url, data=payload, cookies=cookies, headers=headers)
    
    if response.status_code == 200:
        try:
            return response.json()
        except json.JSONDecodeError:
            return {"error": "Failed to parse response", "raw": response.text}
    else:
        return {
            "error": f"Request failed with status code {response.status_code}",
            "raw": response.text
        }
