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

def make_api_request(method, url, headers=None, data=None, params=None, retry_on_403=True):
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
        
        if response.status_code == 403 and retry_on_403:
            print_warning("Session expired. Logging in again.")
            username, password = get_credentials()
            login(username=username, password=password)
            return make_api_request(method, url, headers, data, params, retry_on_403=False)
        
        return response
    except Exception as e:
        raise ValueError(f"API request failed: {str(e)}")

def get_logbook_months(logbook_id=""):
    params = {'logBookId': logbook_id} if logbook_id else None
    response = make_api_request('GET', LOGBOOK_GET_MONTHS_URL, params=params)
    
    if response.status_code == 200:
        data = response.json()
        if 'data' in data:
            months_data = {}
            current_year = datetime.now().year
            
            for item in data['data']:
                year = item.get('year') or current_year
                
                months_data[item['monthInt']] = {
                    'logBookHeaderID': item['logBookHeaderID'],
                    'name': item['month'],
                    'isCurrentMonth': item['isCurrentMonth'],
                    'countData': item['countData'],
                    'isWarning': item['isWarning'],
                    'year': year
                }
            return months_data
        else:
            raise ValueError(f"Unexpected response format: {data}")
    else:
        raise ValueError(f"API request failed with status code {response.status_code}")

def check_month_completion_status(months_data):
    completion_status = {}
    
    for month, month_info in months_data.items():
        logbook_header_id = month_info['logBookHeaderID']
        entries_data = get_logbook_entries(logbook_header_id)
        
        if isinstance(entries_data, dict) and not entries_data.get("error"):
            filled_empty = entries_data.get("filledEmpty", 0)
            filled = entries_data.get("filled", 0)
            filled_submit = entries_data.get("filledSubmit", 0)
            
            completion_status[month] = {
                'completed': filled_empty == 0 and filled > 0 and filled_submit == filled,
                'empty_entries': filled_empty,
                'filled_entries': filled,
                'submitted_entries': filled_submit,
                'month_name': month_info['name'],
                'year': month_info['year'],
                'header_id': logbook_header_id
            }
    
    return completion_status

def is_month_available_for_submission(month, year, completion_status):
    prev_month = month - 1
    prev_year = year
    
    if prev_month == 0:
        prev_month = 12
        prev_year -= 1
    
    if prev_month in completion_status:
        if not completion_status[prev_month]['completed']:
            return False, f"Previous month ({completion_status[prev_month]['month_name']} {prev_year}) has unfilled or unsubmitted entries."
    
    if month not in completion_status:
        return False, f"Month {month} of {year} is not available in the logbook system."
    
    return True, None

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

def is_previous_month_completed(current_month, current_year):
    previous_month = current_month - 1
    previous_year = current_year
    
    if previous_month == 0:
        previous_month = 12
        previous_year -= 1
    
    months_data = get_logbook_months()
    
    if previous_month not in months_data:
        print_info(f"No logbook data found for previous month ({previous_month}/{previous_year}).")
        return True, None
    
    logbook_header_id = months_data[previous_month]['logBookHeaderID']
    entries_data = get_logbook_entries(logbook_header_id)
    
    if not entries_data or not isinstance(entries_data, dict) or "error" in entries_data:
        print_warning(f"Could not retrieve data for previous month ({previous_month}/{previous_year}).")
        return True, None
    
    filled_empty = entries_data.get("filledEmpty", 0)
    filled = entries_data.get("filled", 0)
    filled_submit = entries_data.get("filledSubmit", 0)
    
    print_info(f"Previous month status: {filled_empty} unfilled, {filled} filled, {filled_submit} submitted")
    
    month_completed = filled_empty == 0 and filled > 0 and filled_submit == filled
    
    if not month_completed and filled_empty > 0:
        message = (f"Previous month ({previous_month}/{previous_year}) has {filled_empty} "
                  f"unfilled entries. Please complete them first.")
        return False, message
    
    if not month_completed and filled_submit < filled:
        message = (f"Previous month ({previous_month}/{previous_year}) has {filled - filled_submit} "
                  f"entries that are filled but not submitted. Please submit them first.")
        return False, message
    
    return True, None

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
    year = date_obj.year
    
    is_complete, message = is_previous_month_completed(month, year)
    if not is_complete:
        raise ValueError(message)
    
    months_data = get_logbook_months()
    completion_status = check_month_completion_status(months_data)
    available, message = is_month_available_for_submission(month, year, completion_status)
    
    if not available:
        raise ValueError(message)
    
    if month in months_data:
        logbook_header_id = months_data[month]['logBookHeaderID']
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
