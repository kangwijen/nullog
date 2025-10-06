import requests
import json
import sys
from datetime import datetime
from cookies import load_cookies, load_user_agent
from login import login
from config import get_credentials
from utils import format_iso_date, convert_12hour, logger
from constants import (
    LOGBOOK_GET_MONTHS_URL, LOGBOOK_GET_LOGBOOK_URL, 
    LOGBOOK_STUDENT_SAVE_URL, REFERER_URL
)
from display import print_info, print_error, print_success, print_warning

def prepare_request_params():
    try:
        cookies_data = load_cookies()
        if not cookies_data:
            error_msg = "No cookies available. Please login first."
            logger.error(error_msg)
            raise ValueError(error_msg)
                
        cookies = {cookie['name']: cookie['value'] for cookie in cookies_data}
        user_agent = load_user_agent()
        
        logger.debug(f"Prepared request params: {len(cookies)} cookies, user agent: {user_agent[:50]}...")
        return cookies, user_agent
    except Exception as e:
        logger.error(f"Error preparing request parameters: {str(e)}")
        raise

def make_api_request(method, url, headers=None, data=None, params=None, retry_on_403=True):
    try:
        cookies, user_agent = prepare_request_params()
        
        if headers is None:
            headers = {}
        
        if 'User-Agent' not in headers:
            headers['User-Agent'] = user_agent
        
        headers.setdefault('X-Requested-With', 'XMLHttpRequest')
        headers.setdefault('Referer', REFERER_URL)
        
        logger.debug(f"Making {method.upper()} request to {url}")
        
        if method.lower() == 'post':
            headers.setdefault('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8')
            headers.setdefault('Origin', 'https://activity-enrichment.apps.binus.ac.id')
            response = requests.post(url, cookies=cookies, headers=headers, data=data, timeout=30)
        else:
            response = requests.get(url, cookies=cookies, headers=headers, params=params, timeout=30)
        
        logger.debug(f"Response status: {response.status_code}")
        
        if response.status_code == 403 and retry_on_403:
            logger.warning("Session expired (403 error). Attempting to re-login.")
            print_warning("Session expired. Logging in again.")
            try:
                username, password = get_credentials()
                login_result = login(username=username, password=password)
                if not login_result:
                    logger.error("Failed to re-login")
                    print_error("Failed to re-login. Exiting.")
                    sys.exit(1)
                logger.info("Re-login successful, retrying request")
                return make_api_request(method, url, headers, data, params, retry_on_403=False)
            except Exception as e:
                logger.error(f"Error during re-login: {str(e)}")
                print_error(f"Error during re-login: {str(e)}")
                sys.exit(1)
        
        if response.status_code != 200:
            error_msg = f"API request failed with status code {response.status_code}"
            logger.error(f"{error_msg} - URL: {url}")
            logger.error(f"Response: {response.text[:500]}...")
            print_error(error_msg)
            print_error(f"URL: {url}")
            print_error(f"Response: {response.text[:500]}...")
            return None
            
        logger.debug("API request successful")
        return response
    except requests.exceptions.Timeout:
        error_msg = f"API request timed out for {url}"
        logger.error(error_msg)
        print_error(error_msg)
        return None
    except requests.exceptions.ConnectionError:
        error_msg = f"Connection error for {url}"
        logger.error(error_msg)
        print_error(error_msg)
        return None
    except Exception as e:
        error_msg = f"API request failed: {str(e)}"
        logger.error(error_msg)
        print_error(error_msg)
        return None

def get_logbook_months(logbook_id=""):
    try:
        logger.info("Retrieving logbook months")
        params = {'logBookId': logbook_id} if logbook_id else None
        response = make_api_request('GET', LOGBOOK_GET_MONTHS_URL, params=params)
        
        if not response:
            error_msg = "Failed to retrieve logbook months. Exiting."
            logger.error(error_msg)
            print_error(error_msg)
            sys.exit(1)
        
        try:
            data = response.json()
            if not isinstance(data, dict):
                error_msg = f"Unexpected response format: {data}"
                logger.error(error_msg)
                print_error(error_msg)
                sys.exit(1)
                
            if 'data' in data and isinstance(data['data'], list):
                months_data = {}
                current_year = datetime.now().year
                
                for item in data['data']:
                    try:
                        if not all(k in item for k in ['monthInt', 'logBookHeaderID']):
                            logger.warning(f"Skipping incomplete month data: {item}")
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
                        logger.warning(f"Error processing month data: {str(e)}")
                        continue
                
                if not months_data:
                    error_msg = "No valid month data found in the response. Exiting."
                    logger.error(error_msg)
                    print_error(error_msg)
                    sys.exit(1)
                    
                logger.info(f"Successfully retrieved {len(months_data)} months")
                return months_data
            else:
                error_msg = f"Unexpected response format: {data}"
                logger.error(error_msg)
                print_error(error_msg)
                sys.exit(1)
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON response: {response.text[:500]}... Error: {str(e)}"
            logger.error(error_msg)
            print_error(error_msg)
            sys.exit(1)
        except Exception as e:
            error_msg = f"Error processing logbook months: {str(e)}"
            logger.error(error_msg)
            print_error(error_msg)
            sys.exit(1)
    except Exception as e:
        error_msg = f"Unexpected error in get_logbook_months: {str(e)}"
        logger.error(error_msg)
        print_error(error_msg)
        sys.exit(1)

def check_month_completion_status(months_data):
    try:
        logger.info("Checking month completion status")
        completion_status = {}
        
        for month, month_info in months_data.items():
            try:
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
                    logger.debug(f"Month {month} status: {filled_empty} empty, {filled} filled, {filled_submit} submitted")
                else:
                    logger.warning(f"Could not get completion status for month {month}")
            except Exception as e:
                logger.error(f"Error checking completion status for month {month}: {str(e)}")
                continue
        
        logger.info(f"Completed status check for {len(completion_status)} months")
        return completion_status
    except Exception as e:
        logger.error(f"Error in check_month_completion_status: {str(e)}")
        return {}

def is_month_available_for_submission(month, year, completion_status):
    try:
        prev_month = month - 1
        prev_year = year
        
        if prev_month == 0:
            prev_month = 12
            prev_year -= 1
        
        if prev_month in completion_status:
            if completion_status[prev_month]['empty_entries'] > 0:
                message = f"Previous month ({completion_status[prev_month]['month_name']} {prev_year}) has unfilled entries."
                logger.warning(f"Month {month}/{year} not available: {message}")
                return False, message
        
        if month not in completion_status:
            message = f"Month {month} of {year} is not available in the logbook system."
            logger.warning(f"Month {month}/{year} not available: {message}")
            return False, message
        
        logger.debug(f"Month {month}/{year} is available for submission")
        return True, None
    except Exception as e:
        logger.error(f"Error checking month availability for {month}/{year}: {str(e)}")
        return False, f"Error checking availability: {str(e)}"

def get_logbook_entries(logbook_header_id):
    try:
        if not logbook_header_id:
            error_msg = "Invalid logbook header ID"
            logger.error(error_msg)
            print_error(error_msg)
            sys.exit(1)
            
        logger.debug(f"Retrieving logbook entries for header ID: {logbook_header_id}")
        payload = {'logBookHeaderID': logbook_header_id}
        response = make_api_request('POST', LOGBOOK_GET_LOGBOOK_URL, data=payload)
        
        if not response:
            error_msg = "Failed to retrieve logbook entries. Exiting."
            logger.error(error_msg)
            print_error(error_msg)
            sys.exit(1)
        
        try:
            data = response.json()
            logger.debug(f"Successfully retrieved logbook entries")
            return data
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse response: {response.text[:500]}... Error: {str(e)}"
            logger.error(error_msg)
            print_error(error_msg)
            sys.exit(1)
        except Exception as e:
            error_msg = f"Error processing logbook entries: {str(e)}"
            logger.error(error_msg)
            print_error(error_msg)
            sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error in get_logbook_entries: {str(e)}")
        return {"error": str(e)}

def get_entry_for_date(entries_data, target_date):
    try:
        if not entries_data or "data" not in entries_data:
            logger.debug(f"No entries data available for date {target_date}")
            return None
        
        date_str = format_iso_date(target_date)
        logger.debug(f"Looking for entry with date: {date_str}")
        
        for entry in entries_data["data"]:
            if entry["date"] == date_str:
                if entry["id"] != "00000000-0000-0000-0000-000000000000" and entry["clockIn"]:
                    logger.debug(f"Found existing entry for {target_date}")
                    return entry
        
        logger.debug(f"No existing entry found for {target_date}")
        return None
    except Exception as e:
        logger.error(f"Error getting entry for date {target_date}: {str(e)}")
        return None

def is_date_filled(entries_data, target_date):
    try:
        return get_entry_for_date(entries_data, target_date) is not None
    except Exception as e:
        logger.error(f"Error checking if date {target_date} is filled: {str(e)}")
        return False

def is_previous_month_completed(current_month, current_year):
    try:
        previous_month = current_month - 1
        previous_year = current_year
        
        if previous_month == 0:
            previous_month = 12
            previous_year -= 1
        
        logger.info(f"Checking completion status for previous month: {previous_month}/{previous_year}")
        
        months_data = get_logbook_months()
        
        if previous_month not in months_data:
            logger.info(f"No logbook data found for previous month ({previous_month}/{previous_year}).")
            print_info(f"No logbook data found for previous month ({previous_month}/{previous_year}).")
            return True, None
        
        logbook_header_id = months_data[previous_month]['logBookHeaderID']
        entries_data = get_logbook_entries(logbook_header_id)
        
        if not entries_data or not isinstance(entries_data, dict) or "error" in entries_data:
            logger.warning(f"Could not retrieve data for previous month ({previous_month}/{previous_year}).")
            print_warning(f"Could not retrieve data for previous month ({previous_month}/{previous_year}).")
            return True, None
        
        filled_empty = entries_data.get("filledEmpty", 0)
        filled = entries_data.get("filled", 0)
        filled_submit = entries_data.get("filledSubmit", 0)
        
        logger.info(f"Previous month status: {filled_empty} unfilled, {filled} filled, {filled_submit} submitted")
        print_info(f"Previous month status: {filled_empty} unfilled, {filled} filled, {filled_submit} submitted")
        
        if filled_empty > 0:
            message = (f"Previous month ({previous_month}/{previous_year}) has {filled_empty} "
                      f"unfilled entries. Please complete them first.")
            logger.warning(message)
            return False, message
        
        logger.info("Previous month is completed")
        return True, None
    except Exception as e:
        logger.error(f"Error checking previous month completion: {str(e)}")
        return True, None

def submit_logbook(date, activity, clock_in, clock_out, description, force=False):
    try:
        logger.info(f"Submitting logbook entry for {date}")
        
        if not all([date, activity, clock_in, clock_out, description]):
            error_msg = "All logbook fields are required"
            logger.error(error_msg)
            print_error(error_msg)
            return {"error": "Missing required fields"}
            
        try:
            if isinstance(date, str):
                date_obj = datetime.strptime(date, '%Y-%m-%d')
            elif isinstance(date, datetime):
                date_obj = date
            else:
                error_msg = "Date must be a string in YYYY-MM-DD format or a datetime object"
                logger.error(error_msg)
                print_error(error_msg)
                return {"error": "Invalid date format"}
            
            date_str = format_iso_date(date_obj)
            clock_in_12hr = convert_12hour(clock_in)
            clock_out_12hr = convert_12hour(clock_out)
            month = date_obj.month
            year = date_obj.year
            
            logger.debug(f"Formatted data: date={date_str}, clock_in={clock_in_12hr}, clock_out={clock_out_12hr}")
            
            is_complete, message = is_previous_month_completed(month, year)
            if not is_complete:
                logger.error(f"Previous month not completed: {message}")
                print_error(message)
                return {"error": message}
            
            months_data = get_logbook_months()
            if not months_data:
                error_msg = "Failed to retrieve months data"
                logger.error(error_msg)
                print_error(error_msg)
                return {"error": "Failed to retrieve months data"}
                
            completion_status = check_month_completion_status(months_data)
            available, message = is_month_available_for_submission(month, year, completion_status)
            
            if not available:
                logger.error(f"Month not available: {message}")
                print_error(message)
                return {"error": message}
            
            if month in months_data:
                logbook_header_id = months_data[month]['logBookHeaderID']
                logger.info(f"Using LogBookHeaderID {logbook_header_id} for month {month}")
                print_info(f"Using LogBookHeaderID {logbook_header_id} for month {month}")
            else:
                error_msg = f"No LogBookHeaderID found for month {month}. Cannot proceed."
                logger.error(error_msg)
                print_error(error_msg)
                return {"error": f"No LogBookHeaderID found for month {month}"}
            
            entries_data = get_logbook_entries(logbook_header_id)
            existing_entry = get_entry_for_date(entries_data, date_obj.strftime('%Y-%m-%d'))
            
            if existing_entry and not force:
                error_msg = f"Logbook entry for date {date_obj.strftime('%Y-%m-%d')} is already filled."
                logger.warning(error_msg)
                print_error(error_msg)
                return {"error": f"Logbook entry for date {date_obj.strftime('%Y-%m-%d')} is already filled"}
            
            entry_id = "00000000-0000-0000-0000-000000000000"
            if existing_entry and force:
                entry_id = existing_entry["id"]
                logger.warning(f"Modifying existing entry with ID: {entry_id}")
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
            
            logger.debug(f"Submitting payload: {payload}")
            response = make_api_request('POST', LOGBOOK_STUDENT_SAVE_URL, data=payload)
            
            if not response:
                error_msg = "Failed to submit logbook entry"
                logger.error(error_msg)
                print_error(error_msg)
                return {"error": "Failed to submit logbook entry"}
                
            try:
                result = response.json()
                if isinstance(result, dict) and result.get('success') is False:
                    error_msg = f"Server rejected submission: {result.get('message', 'Unknown error')}"
                    logger.error(error_msg)
                    print_error(error_msg)
                    return {"error": result.get('message', 'Unknown error')}
                
                logger.info(f"Logbook submission successful for {date}")
                return result
            except json.JSONDecodeError as e:
                error_msg = f"Failed to parse response: {response.text[:500]}... Error: {str(e)}"
                logger.error(error_msg)
                print_error(error_msg)
                return {"error": "Failed to parse response", "raw": response.text}
        except ValueError as e:
            logger.error(f"Value error in submit_logbook: {str(e)}")
            print_error(str(e))
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Error in submit_logbook: {str(e)}")
            print_error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error in submit_logbook: {str(e)}")
        print_error(f"Unexpected error: {str(e)}")
        return {"error": f"Unexpected error: {str(e)}"}
