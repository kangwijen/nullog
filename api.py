import requests
import json
from datetime import datetime
from cookies import load_cookies, load_user_agent
from login import login
from config import get_credentials
from utils import format_iso_date, convert_12hour
from constants import (
    LOGBOOK_GET_MONTHS_URL, LOGBOOK_GET_LOGBOOK_URL, 
    LOGBOOK_STUDENT_SAVE_URL, REFERER_URL
)
from display import print_info, print_error, print_success, print_warning

def prepare_request_params():
    cookies_data = load_cookies()
    if not cookies_data:
        raise ValueError("No cookies available. Please login first.")
    
    cookies = {cookie['name']: cookie['value'] for cookie in cookies_data}
    user_agent = load_user_agent()
    
    return cookies, user_agent

def make_api_request(method, url, headers=None, data=None, params=None):
    try:
        cookies, user_agent = prepare_request_params()
        
        if headers is None:
            headers = {}
        
        if 'User-Agent' not in headers:
            headers['User-Agent'] = user_agent
        
        headers.setdefault('X-Requested-With', 'XMLHttpRequest')
        headers.setdefault('Referer', REFERER_URL)
        
        if method.lower() == 'post':
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')
            headers.setdefault('Origin', 'https://activity-enrichment.apps.binus.ac.id')
            response = requests.post(url, cookies=cookies, headers=headers, data=data)
        else:
            response = requests.get(url, cookies=cookies, headers=headers, params=params)
        
        if response.status_code == 403:
            print_warning("Session expired. Logging in again.")
            username, password = get_credentials()
            login(username=username, password=password)
            return make_api_request(method, url, headers, data, params)
        
        return response
    except Exception as e:
        raise ValueError(f"API request failed: {str(e)}")

def get_logbook_months(logbook_id=""):
    params = {'logBookId': logbook_id} if logbook_id else None
    response = make_api_request('GET', LOGBOOK_GET_MONTHS_URL, params=params)
    
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
    payload = {'logBookHeaderID': logbook_header_id}
    response = make_api_request('POST', LOGBOOK_GET_LOGBOOK_URL, data=payload)
    
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

def get_entry_for_date(entries_data, target_date):
    if not entries_data or "data" not in entries_data:
        return None
    
    date_str = format_iso_date(target_date)
    
    for entry in entries_data["data"]:
        if entry["date"] == date_str:
            if entry["id"] != "00000000-0000-0000-0000-000000000000" and entry["clockIn"]:
                return entry
    
    return None

def is_date_filled(entries_data, target_date):
    return get_entry_for_date(entries_data, target_date) is not None

def submit_logbook(date, activity, clock_in, clock_out, description, force=False):
    if isinstance(date, str):
        date_obj = datetime.strptime(date, '%Y-%m-%d')
    elif isinstance(date, datetime):
        date_obj = date
    else:
        raise ValueError("Date must be a string in YYYY-MM-DD format or a datetime object")
    
    date_str = format_iso_date(date_obj)
    clock_in_12hr = convert_12hour(clock_in)
    clock_out_12hr = convert_12hour(clock_out)
    month = date_obj.month
    
    month_mapping = get_logbook_months()
    if month in month_mapping:
        logbook_header_id = month_mapping[month]
        print_info(f"Using LogBookHeaderID {logbook_header_id} for month {month}")
    else:
        raise ValueError(f"No LogBookHeaderID found for month {month}. Cannot proceed.")
    
    entries_data = get_logbook_entries(logbook_header_id)
    existing_entry = get_entry_for_date(entries_data, date_obj.strftime('%Y-%m-%d'))
    
    if existing_entry and not force:
        raise ValueError(f"Logbook entry for date {date_obj.strftime('%Y-%m-%d')} is already filled.")
    
    entry_id = "00000000-0000-0000-0000-000000000000"
    if existing_entry and force:
        entry_id = existing_entry["id"]
        print_warning(f"Modifying existing entry with ID: {entry_id}")

    payload = {
        "model[ID]": entry_id,
        "model[LogBookHeaderID]": logbook_header_id,
        "model[Date]": date_str,
        "model[Activity]": activity,
        "model[ClockIn]": clock_in_12hr,
        "model[ClockOut]": clock_out_12hr,
        "model[Description]": description,
        "model[flagjulyactive]": "false"
    }
    
    response = make_api_request('POST', LOGBOOK_STUDENT_SAVE_URL, data=payload)
    
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
