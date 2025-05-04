import requests
import json
import sys
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
            login_result = login(username=username, password=password)
            if not login_result:
                print_error("Failed to re-login. Exiting.")
                sys.exit(1)
            return make_api_request(method, url, headers, data, params, retry_on_403=False)
        
        if response.status_code != 200:
            print_error(f"API request failed with status code {response.status_code}")
            print_error(f"URL: {url}")
            print_error(f"Response: {response.text[:500]}...")
            return None
            
        return response
    except Exception as e:
        print_error(f"API request failed: {str(e)}")
        return None

def get_logbook_months(logbook_id=""):
    params = {'logBookId': logbook_id} if logbook_id else None
    response = make_api_request('GET', LOGBOOK_GET_MONTHS_URL, params=params)
    
    if not response:
        print_error("Failed to retrieve logbook months. Exiting.")
        sys.exit(1)
    
    try:
        data = response.json()
        if not isinstance(data, dict):
            print_error(f"Unexpected response format: {data}")
            sys.exit(1)
            
        if 'data' in data and isinstance(data['data'], list):
            months_data = {}
            current_year = datetime.now().year
            
            for item in data['data']:
                try:
                    if not all(k in item for k in ['monthInt', 'logBookHeaderID']):
                        print_warning(f"Skipping incomplete month data: {item}")
                        continue
                    
                    year = item.get('year') or current_year
                    
                    months_data[item['monthInt']] = {
                        'logBookHeaderID': item['logBookHeaderID'],
                        'name': item.get('month', f"Month {item['monthInt']}"),
                        'isCurrentMonth': item.get('isCurrentMonth', False),
                        'countData': item.get('countData', 0),
                        'isWarning': item.get('isWarning', False),
                        'year': year
                    }
                except Exception as e:
                    print_warning(f"Error processing month data: {str(e)}")
                    continue
            
            if not months_data:
                print_error("No valid month data found in the response. Exiting.")
                sys.exit(1)
                
            return months_data
        else:
            print_error(f"Unexpected response format: {data}")
            sys.exit(1)
    except json.JSONDecodeError:
        print_error(f"Invalid JSON response: {response.text[:500]}...")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error processing logbook months: {str(e)}")
        sys.exit(1)

def check_month_completion_status(months_data):
    completion_status = {}
    
    for month, month_info in months_data.items():
        logbook_header_id = month_info['logBookHeaderID']
        entries_data = get_logbook_entries(logbook_header_id)
        
        if isinstance(entries_data, dict) and not entries_data.get("error"):
            filled_empty = entries_data.get("filledEmpty", 0)
            filled = entries_data.get("filled", 0)
            filled_submit = entries_data.get("filledSubmit", 0)
            filled_all = entries_data.get("filledAll", filled)
            completed = filled_empty == 0
            completion_status[month] = {
                'completed': completed,
                'empty_entries': filled_empty,
                'filled_entries': filled,
                'submitted_entries': filled_submit,
                'filledSubmit': filled_submit,
                'filledAll': filled_all,
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
        if completion_status[prev_month]['empty_entries'] > 0:
            return False, f"Previous month ({completion_status[prev_month]['month_name']} {prev_year}) has unfilled entries."
    
    if month not in completion_status:
        return False, f"Month {month} of {year} is not available in the logbook system."
    
    return True, None

def get_logbook_entries(logbook_header_id):
    if not logbook_header_id:
        print_error("Invalid logbook header ID")
        sys.exit(1)
        
    payload = {'logBookHeaderID': logbook_header_id}
    response = make_api_request('POST', LOGBOOK_GET_LOGBOOK_URL, data=payload)
    
    if not response:
        print_error("Failed to retrieve logbook entries. Exiting.")
        sys.exit(1)
    
    try:
        return response.json()
    except json.JSONDecodeError:
        print_error(f"Failed to parse response: {response.text[:500]}...")
        sys.exit(1)
    except Exception as e:
        print_error(f"Error processing logbook entries: {str(e)}")
        sys.exit(1)

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
    
    if filled_empty > 0:
        message = (f"Previous month ({previous_month}/{previous_year}) has {filled_empty} "
                  f"unfilled entries. Please complete them first.")
        return False, message
    
    return True, None

def submit_logbook(date, activity, clock_in, clock_out, description, force=False):
    if not all([date, activity, clock_in, clock_out, description]):
        print_error("All logbook fields are required")
        return {"error": "Missing required fields"}
        
    try:
        if isinstance(date, str):
            date_obj = datetime.strptime(date, '%Y-%m-%d')
        elif isinstance(date, datetime):
            date_obj = date
        else:
            print_error("Date must be a string in YYYY-MM-DD format or a datetime object")
            return {"error": "Invalid date format"}
        
        date_str = format_iso_date(date_obj)
        clock_in_12hr = convert_12hour(clock_in)
        clock_out_12hr = convert_12hour(clock_out)
        month = date_obj.month
        year = date_obj.year
        
        is_complete, message = is_previous_month_completed(month, year)
        if not is_complete:
            print_error(message)
            return {"error": message}
        
        months_data = get_logbook_months()
        if not months_data:
            print_error("Failed to retrieve months data")
            return {"error": "Failed to retrieve months data"}
            
        completion_status = check_month_completion_status(months_data)
        available, message = is_month_available_for_submission(month, year, completion_status)
        
        if not available:
            print_error(message)
            return {"error": message}
        
        if month in months_data:
            logbook_header_id = months_data[month]['logBookHeaderID']
            print_info(f"Using LogBookHeaderID {logbook_header_id} for month {month}")
        else:
            print_error(f"No LogBookHeaderID found for month {month}. Cannot proceed.")
            return {"error": f"No LogBookHeaderID found for month {month}"}
        
        entries_data = get_logbook_entries(logbook_header_id)
        existing_entry = get_entry_for_date(entries_data, date_obj.strftime('%Y-%m-%d'))
        
        if existing_entry and not force:
            print_error(f"Logbook entry for date {date_obj.strftime('%Y-%m-%d')} is already filled.")
            return {"error": f"Logbook entry for date {date_obj.strftime('%Y-%m-%d')} is already filled"}
        
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
        
        if not response:
            print_error("Failed to submit logbook entry")
            return {"error": "Failed to submit logbook entry"}
            
        try:
            result = response.json()
            if isinstance(result, dict) and result.get('success') is False:
                print_error(f"Server rejected submission: {result.get('message', 'Unknown error')}")
                return {"error": result.get('message', 'Unknown error')}
            return result
        except json.JSONDecodeError:
            print_error(f"Failed to parse response: {response.text[:500]}...")
            return {"error": "Failed to parse response", "raw": response.text}
    except ValueError as e:
        print_error(str(e))
        return {"error": str(e)}
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}
