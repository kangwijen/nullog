from utils.cookies import load_cookies
from utils.login import login
from utils.api import (
    submit_logbook, get_logbook_months, get_logbook_entries, get_entry_for_date,
    check_month_completion_status, is_month_available_for_submission
)
from utils.config import get_credentials
from datetime import datetime
from utils.csv_parser import import_from_csv
from utils.utils import is_valid_time_format, logger
from utils.constants import WEEKDAY_SATURDAY, WEEKDAY_SUNDAY
from utils.display import (
    print_success, print_error, print_warning, print_info, print_header, 
    display_csv_entries, display_available_months
)
import sys
import os
import random
import time
import requests

LATEST_VERSION_URL_PRIMARY = "https://raw.githubusercontent.com/kangwijen/nullog/refs/heads/main/VERSION"

def _parse_version(version_str):
    try:
        parts = version_str.strip().split(".")
        return tuple(int(p) for p in parts)
    except Exception:
        return (0, 0, 0)

def _load_local_version():
    try:
        base_dir = os.path.dirname(__file__)
        version_path = os.path.join(base_dir, "VERSION")
        if os.path.exists(version_path):
            with open(version_path, "r", encoding="utf-8") as f:
                file_version = f.read().strip()
                parsed = _parse_version(file_version)
                if parsed != (0, 0, 0):
                    return file_version
        return "0.0.0"
    except Exception:
        return "0.0.0"

def _fetch_remote_version(url):
    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            return response.text.strip()
        logger.warning(f"Update check failed at {url} with status code: {response.status_code}")
        return None
    except requests.exceptions.Timeout:
        logger.warning(f"Update check timed out for {url}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Update check failed for {url}: {str(e)}")
        return None

def check_for_update():
    try:
        logger.info("Checking for software updates")
        latest_primary = _fetch_remote_version(LATEST_VERSION_URL_PRIMARY)

        latest_version = latest_primary
        if latest_version:
            latest_tuple = _parse_version(latest_version)
            local_version = _load_local_version()
            current_tuple = _parse_version(local_version)

            if latest_tuple > current_tuple:
                logger.info(f"New version available: {latest_version}")
                print_warning(f"A new version ({latest_version}) is available. You are using {local_version}.")
                print_warning("Please pull the latest version from GitHub.")
            elif latest_tuple == current_tuple:
                logger.info("Using latest version")
                print_success("You are using the latest version.")
            else:
                logger.info("Local version is newer than remote VERSION")
                print_success(f"You are ahead of the remote release (local {local_version} > remote {latest_version}).")

        else:
            logger.warning("Could not check for updates (all endpoints failed)")
            print_info("Could not check for updates (network or server error)")
    except requests.exceptions.Timeout:
        logger.warning("Update check timed out")
        print_info("Could not check for updates (timeout)")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Update check failed: {str(e)}")
        print_info("Could not check for updates (network error)")
    except Exception as e:
        logger.error(f"Unexpected error during update check: {str(e)}")
        print_info("Could not check for updates (unexpected error)")

def validate_date_range(year, month, start, end, current_date):
    try:
        if not isinstance(start, int) or not isinstance(end, int):
            print_error("Start and end dates must be numbers")
            return False
        
        if not 1 <= start <= 31:
            print_error("Start date must be between 1 and 31")
            return False
        
        if year != current_date.year:
            print_error("Year must be the current year")
            return False
        
        if year == current_date.year and month == current_date.month and start > current_date.day:
            print_error("Start date cannot be in the future")
            return False
                
        if not 1 <= end <= 31 or end < start:
            print_error("End date must be between 1 and 31 and greater than or equal to start date")
            return False
        
        if year == current_date.year and month == current_date.month and end > current_date.day:
            print_error("End date cannot be in the future")
            return False
        
        logger.info(f"Date range validation passed: {start}-{end}/{month}/{year}")
        return True
    except Exception as e:
        logger.error(f"Error validating date range: {str(e)}")
        print_error(f"Error validating date range: {str(e)}")
        return False

def validate_time_input(time_str, label):
    try:
        if not isinstance(time_str, str):
            print_error(f"{label} must be a string")
            return False
        
        time_str = time_str.strip()
        if not time_str:
            print_error(f"{label} cannot be empty")
            return False
        
        if not is_valid_time_format(time_str):
            print_error(f"{label} must be in format HH:MM (24-hour) or OFF")
            return False
        
        logger.debug(f"Time validation passed for {label}: {time_str}")
        return True
    except Exception as e:
        logger.error(f"Error validating time input '{time_str}' for {label}: {str(e)}")
        print_error(f"Error validating {label}: {str(e)}")
        return False

def validate_clock_times(clock_in, clock_out):
    try:
        if clock_in != "OFF" and clock_out != "OFF":
            clock_in_hour, clock_in_min = map(int, clock_in.split(':'))
            clock_out_hour, clock_out_min = map(int, clock_out.split(':'))
            if (clock_out_hour < clock_in_hour) or (clock_out_hour == clock_in_hour and clock_out_min <= clock_in_min):
                print_error("Clock out time must be later than clock in time")
                return False
        
        logger.debug(f"Clock time validation passed: {clock_in} - {clock_out}")
        return True
    except Exception as e:
        logger.error(f"Error validating clock times: {str(e)}")
        print_error(f"Error validating clock times: {str(e)}")
        return False

def get_user_input():
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    current_day = current_date.day
    
    logger.info("Starting user input collection")
    
    while True:
        try:
            # Get start date
            print_info("Start date (1-31):")
            start_input = input().strip()
            if not start_input:
                print_error("Start date cannot be empty")
                continue
            
            try:
                start = int(start_input)
            except ValueError:
                print_error("Start date must be a number")
                continue
            
            # Get end date
            print_info("End Date (1-31):")
            end_input = input().strip()
            if not end_input:
                print_error("End date cannot be empty")
                continue
            
            try:
                end = int(end_input)
            except ValueError:
                print_error("End date must be a number")
                continue
            
            if not validate_date_range(year, month, start, end, current_date):
                continue
            
            # Get clock in time
            print_info("Clock in time (24-hour format, e.g. 09:00 or OFF):")
            clock_in = input().strip()
            if not validate_time_input(clock_in, "Clock in"):
                continue
                
            # Get clock out time
            print_info("Clock out time (24-hour format, e.g. 18:00 or OFF):")
            clock_out = input().strip()
            if not validate_time_input(clock_out, "Clock out"):
                continue
            
            if not validate_clock_times(clock_in, clock_out):
                continue
                
            # Get activity
            print_info("Activity: ")
            activity = input().strip()
            if not activity:
                print_error("Activity cannot be empty")
                continue
                
            # Get description
            print_info("Description: ")
            description = input().strip()
            if not description:
                print_error("Description cannot be empty")
                continue
            
            # Get force overwrite preference
            print_info("Do you want to force overwrite all existing entries? (y/n):")
            force_overwrite_input = input().strip().lower()
            force_overwrite = force_overwrite_input == 'y'
            
            logger.info("User input collection completed successfully")
            
            return {
                'start_date': start,
                'end_date': end,
                'year': year,
                'month': month,
                'activity': activity,
                'clock_in': clock_in,
                'clock_out': clock_out,
                'description': description,
                'force_overwrite': force_overwrite
            }
        except KeyboardInterrupt:
            logger.info("User interrupted input collection")
            print_warning("\nInput cancelled by user.")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during user input: {str(e)}")
            print_error(f"Unexpected error: {str(e)}")
            continue

def generate_date_range(start_date, end_date, year, month):
    try:
        dates = []
        sundays = []
        
        for day in range(start_date, end_date + 1):
            try:
                date_obj = datetime(year, month, day)
                date_str = date_obj.strftime('%Y-%m-%d')
                
                if date_obj.weekday() == WEEKDAY_SUNDAY:
                    sundays.append(date_str)
                else:
                    dates.append(date_str)
            except ValueError as e:
                logger.warning(f"Invalid date: {year}-{month}-{day}, skipping... Error: {str(e)}")
                print_warning(f"Invalid date: {year}-{month}-{day}, skipping...")
        
        logger.info(f"Generated date range: {len(dates)} workdays, {len(sundays)} Sundays")
        return dates, sundays
    except Exception as e:
        logger.error(f"Error generating date range: {str(e)}")
        print_error(f"Error generating date range: {str(e)}")
        return [], []

def process_single_day(date, activity, clock_in, clock_out, description, existing_entries, force_overwrite=False):
    try:
        logger.info(f"Processing single day entry for {date}")
        
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        weekday = date_obj.weekday()
        
        if weekday == WEEKDAY_SUNDAY:
            logger.info(f"Skipping Sunday: {date}")
            print_warning(f"Skipping Sunday: {date}")
            return
        
        existing_entry = get_entry_for_date(existing_entries, date)
        if existing_entry:
            logger.info(f"Found existing entry for {date}")
            print_info(f"Entry already exists for {date}:")
            print_info(f"  Activity: {existing_entry['activity']}")
            print_info(f"  Clock In: {existing_entry['clockIn']}")
            print_info(f"  Clock Out: {existing_entry['clockOut']}")
            print_info(f"  Description: {existing_entry['description']}")
            
            if not force_overwrite:
                try:
                    confirm = input(f"Do you want to overwrite this entry for {date}? (y/n): ").strip().lower()
                    if confirm != 'y':
                        logger.info(f"User chose not to overwrite entry for {date}")
                        print_warning(f"Skipping {date}...")
                        return
                    logger.info(f"User confirmed overwriting entry for {date}")
                    print_info(f"Confirmed overwriting entry for {date}")
                except KeyboardInterrupt:
                    logger.info("User interrupted overwrite confirmation")
                    print_warning("\nOverwrite cancelled by user.")
                    return
        
        logger.info(f"Submitting logbook for date: {date}")
        print_info(f"Submitting logbook for date: {date}")
        
        try:
            if weekday == WEEKDAY_SATURDAY:
                saturday_submission = os.getenv("SATURDAY_SUBMISSION", "false").lower() == "true"
                
                if not saturday_submission:
                    logger.info(f"Saturday detected - submitting as OFF day for {date}")
                    print_warning(f"Saturday detected - submitting as OFF day")
                    response = submit_logbook(
                        date=date,
                        activity="OFF",
                        clock_in="OFF",
                        clock_out="OFF",
                        description="OFF",
                        force=True if existing_entry else force_overwrite
                    )
                else:
                    logger.info(f"Saturday detected - submitting with provided values for {date}")
                    print_warning(f"Saturday detected - submitting with provided values")
                    response = submit_logbook(
                        date=date,
                        activity=activity,
                        clock_in=clock_in,
                        clock_out=clock_out,
                        description=description,
                        force=True if existing_entry else force_overwrite
                    )
            else:
                response = submit_logbook(
                    date=date,
                    activity=activity,
                    clock_in=clock_in,
                    clock_out=clock_out,
                    description=description,
                    force=True if existing_entry else force_overwrite
                )
            
            if "error" in response:
                logger.error(f"Logbook submission failed for {date}: {response['error']}")
                print_error(f"Logbook submission failed: {response['error']}")
                return False
            else:
                logger.info(f"Logbook entry for {date} submitted successfully")
                print_success(f"Logbook entry for {date} submitted successfully")
                return True
        except Exception as e:
            logger.error(f"Cannot submit entry for {date}: {str(e)}")
            print_error(f"Cannot submit entry for {date}: {str(e)}")
            return False
        finally:
            logger.info(f"Waiting before next submission...")
            print("Waiting for 1-3 seconds before next submission...")
            time.sleep(random.uniform(1, 3))
    except ValueError as e:
        logger.error(f"Invalid date format for {date}: {str(e)}")
        print_error(f"Invalid date format for {date}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error processing {date}: {str(e)}")
        print_error(f"Unexpected error processing {date}: {str(e)}")
        return False

def group_entries_by_month(csv_entries):
    try:
        entries_by_month = {}
        for entry in csv_entries:
            try:
                date_obj = datetime.strptime(entry['date'], '%Y-%m-%d')
                month = date_obj.month
                year = date_obj.year
                month_key = (year, month)
                
                if month_key not in entries_by_month:
                    entries_by_month[month_key] = []
                    
                entries_by_month[month_key].append(entry)
            except ValueError as e:
                logger.error(f"Invalid date format in entry: {entry.get('date', 'unknown')} - {str(e)}")
                continue
            except Exception as e:
                logger.error(f"Error processing entry: {str(e)}")
                continue
        
        logger.info(f"Grouped entries by month: {len(entries_by_month)} months")
        return entries_by_month
    except Exception as e:
        logger.error(f"Error grouping entries by month: {str(e)}")
        return {}

def process_csv_input():
    try:
        logger.info("Starting CSV input processing")
        csv_entries, csv_errors = import_from_csv()
        
        if not csv_entries:
            logger.error("No valid entries found in CSV")
            print_error("No valid entries found in CSV. Exiting.")
            return False
        
        logger.info(f"Successfully imported {len(csv_entries)} entries from CSV")
        display_csv_entries(csv_entries)
        
        if csv_errors:
            logger.warning(f"Found {len(csv_errors)} CSV validation errors/warnings")
            print_header("Validation Errors and Warnings")
            for error in csv_errors:
                if "Sunday entries" in error:
                    print_warning(error)
                else:
                    print_error(error)
            print()
        
        try:
            print_info("Do you want to continue with these entries? (y/n):")
            user_input = input().strip().lower()
            if user_input != 'y':
                logger.info("User cancelled CSV processing")
                print_warning("Operation cancelled by user.")
                return False
        except KeyboardInterrupt:
            logger.info("User interrupted CSV processing confirmation")
            print_warning("\nOperation cancelled by user.")
            return False
        
        try:
            logger.info("Retrieving logbook months")
            months_data = get_logbook_months()
            if not months_data:
                logger.error("Failed to retrieve logbook months")
                print_error("Failed to retrieve logbook months. Exiting.")
                sys.exit(1)
            
            logger.info("Checking month completion status")
            completion_status = check_month_completion_status(months_data)
            
            display_available_months(completion_status)
            
            logger.info("Grouping entries by month")
            entries_by_month = group_entries_by_month(csv_entries)
            
            if not entries_by_month:
                logger.error("No valid entries to process after grouping")
                print_error("No valid entries to process. Exiting.")
                return False
            
            unavailable_months = []
            for (year, month) in entries_by_month.keys():
                if month not in months_data:
                    month_name = datetime(year, month, 1).strftime('%B')
                    unavailable_months.append(f"{month_name} {year}")
            
            if unavailable_months:
                logger.error(f"Unavailable months found: {unavailable_months}")
                print_error(f"The following months in your CSV are not available in the logbook system:")
                for month in unavailable_months:
                    print_error(f"  - {month}")
                
                print_error("Please check your CSV file and try again.")
                return False
            
            try:
                print_info("Do you want to force overwrite EXISTING entries without individual confirmation? (y/n):")
                force_overwrite_input = input().strip().lower()
                force_overwrite = force_overwrite_input == 'y'
                
                if force_overwrite:
                    logger.warning("User enabled force overwrite mode")
                    print_warning("All existing entries will be overwritten without further confirmation!")
                    print_warning("Note: Previous month validation will still be enforced. You cannot submit to a month if previous months are incomplete.")
                else:
                    logger.info("User chose individual confirmation mode")
                    print_info("You will be prompted for confirmation before overwriting each existing entry.")
            except KeyboardInterrupt:
                logger.info("User interrupted force overwrite confirmation")
                print_warning("\nOperation cancelled by user.")
                return False
            
            validated_entries = {}
            
            for (year, month), entries in entries_by_month.items():
                if month not in months_data:
                    continue
                    
                available, message = is_month_available_for_submission(month, year, completion_status)
                
                if not available:
                    logger.error(f"Month {month}/{year} not available: {message}")
                    print_error(f"Cannot submit entries for {months_data[month]['name']} {year}: {message}")
                    print_error(f"Skipping entries for {months_data[month]['name']} {year}. Please complete previous months first.")
                else:
                    validated_entries[(year, month)] = entries
            
            if not validated_entries:
                logger.error("No valid entries to submit after validation")
                print_error("No valid entries to submit after validation. Exiting.")
                return False
            
            success_count = 0
            total_entries = sum(len(entries) for entries in validated_entries.values())
            
            logger.info(f"Starting submission of {total_entries} entries across {len(validated_entries)} months")
            
            for (year, month), entries in validated_entries.items():
                logbook_header_id = months_data[month]['logBookHeaderID']
                logger.info(f"Processing month {month}/{year} with header ID {logbook_header_id}")
                print_info(f"Using LogBookHeaderID {logbook_header_id} for {months_data[month]['name']} {year}")
                
                try:
                    existing_entries = get_logbook_entries(logbook_header_id)
                    if "error" in existing_entries:
                        logger.error(f"Error fetching existing entries for {months_data[month]['name']} {year}: {existing_entries['error']}")
                        print_error(f"Error fetching existing entries for {months_data[month]['name']} {year}: {existing_entries['error']}")
                        continue
                except Exception as e:
                    logger.error(f"Error fetching existing entries for {months_data[month]['name']} {year}: {str(e)}")
                    print_error(f"Error fetching existing entries for {months_data[month]['name']} {year}: {str(e)}")
                    continue
                
                for entry in entries:
                    try:
                        if process_single_day(
                            date=entry['date'],
                            activity=entry['activity'],
                            clock_in=entry['clock_in'],
                            clock_out=entry['clock_out'],
                            description=entry['description'],
                            existing_entries=existing_entries,
                            force_overwrite=force_overwrite
                        ):
                            success_count += 1
                    except Exception as e:
                        logger.error(f"Error processing entry for {entry.get('date', 'unknown')}: {str(e)}")
                        print_error(f"Error processing entry for {entry.get('date', 'unknown')}: {str(e)}")
                        continue

                
            
            logger.info(f"CSV processing completed: {success_count}/{total_entries} entries submitted successfully")
            print_info(f"Successfully submitted {success_count} out of {total_entries} entries")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error during CSV processing: {str(e)}")
            print_error(f"An error occurred while processing CSV: {str(e)}")
            return False
    except KeyboardInterrupt:
        logger.info("CSV processing interrupted by user")
        print_warning("\nOperation cancelled by user.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during CSV processing: {str(e)}")
        print_error(f"Unexpected error: {str(e)}")
        return False

def main():
    try:
        logger.info("Starting nullog application")
        check_for_update()
        
        print_header("nullog - Automated Logbook System")
        print_header("DISCLAIMER")
        print_info("This tool automates logbook entries and may modify existing data on your behalf.")
        print_info("By using this tool, you acknowledge that:")
        print_info("1. You take full responsibility for all entries submitted through this tool")
        print_info("2. You have verified that all data to be submitted is accurate and complete")
        print_info("3. You understand that existing entries may be overwritten without recovery")
        print_info("4. This tool is provided as-is with no warranty or guarantees of any kind")
        print_info("5. The developers are not responsible for any issues arising from its use")
        
        try:
            print_info("\nDo you accept these terms and wish to continue? (y/n):")
            user_input = input().strip().lower()
            if user_input != 'y':
                logger.info("User declined disclaimer")
                print_warning("You must accept the disclaimer to use this tool. Exiting...")
                sys.exit(0)
        except KeyboardInterrupt:
            logger.info("User interrupted disclaimer acceptance")
            print_warning("\nYou must accept the disclaimer to use this tool. Exiting...")
            sys.exit(0)
        
        logger.info("User accepted disclaimer")
        
        # Always perform fresh login session
        try:
            logger.info("Starting fresh login session")
            print_info("Starting fresh login session...")
            username, password = get_credentials()
            login_result = login(username=username, password=password)
            if not login_result:
                logger.error("Login failed")
                print_error("Failed to log in. Please try again.")
                sys.exit(1)
            cookies = load_cookies()
            if not cookies:
                logger.error("Failed to save login session")
                print_error("Failed to save login session. Exiting.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error during session management: {str(e)}")
            print_error(f"Error during session management: {str(e)}")
            sys.exit(1)
        
        # Process CSV input
        try:
            if not process_csv_input():
                logger.warning("CSV processing completed with errors or no entries were processed")
                print_warning("Program completed with errors or no entries were processed.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Error during CSV processing: {str(e)}")
            print_error(f"Error during CSV processing: {str(e)}")
            sys.exit(1)
        
        logger.info("Program completed successfully")
        print_success("Program completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
        print_warning("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error in main function: {str(e)}")
        print_error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
