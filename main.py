from cookies import load_cookies
from login import login
from api import (
    submit_logbook, get_logbook_months, get_logbook_entries, get_entry_for_date,
    check_month_completion_status, is_month_available_for_submission
)
from config import get_credentials
from datetime import datetime
from csv_parser import import_from_csv
from utils import is_valid_time_format
from constants import WEEKDAY_SATURDAY, WEEKDAY_SUNDAY
from display import (
    print_success, print_error, print_warning, print_info, print_header, 
    display_csv_entries, display_available_months
)
import sys

def validate_date_range(year, month, start, end, current_date):
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
    
    return True

def validate_time_input(time_str, label):
    if not is_valid_time_format(time_str):
        print_error(f"{label} must be in format HH:MM (24-hour) or OFF")
        return False
    return True

def validate_clock_times(clock_in, clock_out):
    if clock_in != "OFF" and clock_out != "OFF":
        clock_in_hour, clock_in_min = map(int, clock_in.split(':'))
        clock_out_hour, clock_out_min = map(int, clock_out.split(':'))
        if (clock_out_hour < clock_in_hour) or (clock_out_hour == clock_in_hour and clock_out_min <= clock_in_min):
            print_error("Clock out time must be later than clock in time")
            return False
    return True

def get_user_input():
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    current_day = current_date.day
    
    while True:
        try:
            print_info("Start date (1-31):")
            start = int(input())
            
            print_info("End Date (1-31):")
            end = int(input())
            
            if not validate_date_range(year, month, start, end, current_date):
                continue
            
            print_info("Clock in time (24-hour format, e.g. 09:00 or OFF):")
            clock_in = input().strip()
            if not validate_time_input(clock_in, "Clock in"):
                continue
                
            print_info("Clock out time (24-hour format, e.g. 18:00 or OFF):")
            clock_out = input().strip()
            if not validate_time_input(clock_out, "Clock out"):
                continue
            
            if not validate_clock_times(clock_in, clock_out):
                continue
                
            print_info("Activity: ")
            activity = input()
            if not activity:
                print_error("Activity cannot be empty")
                continue
                
            print_info("Description: ")
            description = input()
            if not description:
                print_error("Description cannot be empty")
                continue
            
            print_info("Do you want to force overwrite all existing entries? (y/n):")
            force_overwrite = input().strip().lower() == 'y'
            
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
        except ValueError:
            print_error("Please enter valid numbers for dates and times")

def generate_date_range(start_date, end_date, year, month):
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
        except ValueError:
            print_warning(f"Invalid date: {year}-{month}-{day}, skipping...")
    
    return dates, sundays

def process_single_day(date, activity, clock_in, clock_out, description, existing_entries, force_overwrite=False):
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    weekday = date_obj.weekday()
    
    if weekday == WEEKDAY_SUNDAY:
        print_warning(f"Skipping Sunday: {date}")
        return
    
    existing_entry = get_entry_for_date(existing_entries, date)
    if existing_entry:
        print_info(f"Entry already exists for {date}:")
        print_info(f"  Activity: {existing_entry['activity']}")
        print_info(f"  Clock In: {existing_entry['clockIn']}")
        print_info(f"  Clock Out: {existing_entry['clockOut']}")
        print_info(f"  Description: {existing_entry['description']}")
        
        if not force_overwrite:
            confirm = input(f"Do you want to overwrite this entry for {date}? (y/n): ").strip().lower()
            if confirm != 'y':
                print_warning(f"Skipping {date}...")
                return
            print_info(f"Confirmed overwriting entry for {date}")
    
    print_info(f"Submitting logbook for date: {date}")
    
    try:
        if weekday == WEEKDAY_SATURDAY:
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
            response = submit_logbook(
                date=date,
                activity=activity,
                clock_in=clock_in,
                clock_out=clock_out,
                description=description,
                force=True if existing_entry else force_overwrite
            )
        
        if "error" in response:
            print_error(f"Logbook submission failed: {response['error']}")
        else:
            print_success(f"Logbook entry for {date} submitted successfully")
    except ValueError as e:
        print_error(f"Cannot submit entry for {date}: {str(e)}")
        return

def group_entries_by_month(csv_entries):
    entries_by_month = {}
    for entry in csv_entries:
        date_obj = datetime.strptime(entry['date'], '%Y-%m-%d')
        month = date_obj.month
        year = date_obj.year
        month_key = (year, month)
        
        if month_key not in entries_by_month:
            entries_by_month[month_key] = []
            
        entries_by_month[month_key].append(entry)
    
    return entries_by_month

def process_csv_input():
    csv_entries = import_from_csv()
    if not csv_entries:
        print_error("No valid entries found in CSV. Exiting.")
        return False
    
    display_csv_entries(csv_entries)
    
    months_data = get_logbook_months()
    completion_status = check_month_completion_status(months_data)
    
    display_available_months(completion_status)
    
    entries_by_month = group_entries_by_month(csv_entries)
    
    unavailable_months = []
    for (year, month) in entries_by_month.keys():
        if month not in months_data:
            month_name = datetime(year, month, 1).strftime('%B')
            unavailable_months.append(f"{month_name} {year}")
    
    if unavailable_months:
        print_error(f"The following months in your CSV are not available in the logbook system:")
        for month in unavailable_months:
            print_error(f"  - {month}")

        print_error("Please check your CSV file and try again.")
        
        sys.exit(1)
    
    print_info("Do you want to force overwrite EXISTING entries without individual confirmation? (y/n):")
    force_overwrite = input().strip().lower() == 'y'
    
    if force_overwrite:
        print_warning("All existing entries will be overwritten without further confirmation!")
        print_warning("Note: Previous month validation will still be enforced. You cannot submit to a month if previous months are incomplete.")
    else:
        print_info("You will be prompted for confirmation before overwriting each existing entry.")
    
    validated_entries = {}
    
    for (year, month), entries in entries_by_month.items():
        if month not in months_data:
            continue
            
        available, message = is_month_available_for_submission(month, year, completion_status)
        
        if not available:
            print_error(f"Cannot submit entries for {months_data[month]['name']} {year}: {message}")
            print_error(f"Skipping entries for {months_data[month]['name']} {year}. Please complete previous months first.")
        else:
            validated_entries[(year, month)] = entries
    
    if not validated_entries:
        print_error("No valid entries to submit after validation. Exiting.")
        return False
    
    for (year, month), entries in validated_entries.items():
        logbook_header_id = months_data[month]['logBookHeaderID']
        print_info(f"Using LogBookHeaderID {logbook_header_id} for {months_data[month]['name']} {year}")
        
        existing_entries = get_logbook_entries(logbook_header_id)
        if "error" in existing_entries:
            print_error(f"Error fetching existing entries for {months_data[month]['name']} {year}: {existing_entries['error']}")
            continue
        
        for entry in entries:
            process_single_day(
                date=entry['date'],
                activity=entry['activity'],
                clock_in=entry['clock_in'],
                clock_out=entry['clock_out'],
                description=entry['description'],
                existing_entries=existing_entries,
                force_overwrite=force_overwrite
            )
    
    return True

def main():
    print_header("nullog - Automated Logbook System")
    print_header("DISCLAIMER")
    print_info("This tool automates logbook entries and may modify existing data on your behalf.")
    print_info("By using this tool, you acknowledge that:")
    print_info("1. You take full responsibility for all entries submitted through this tool")
    print_info("2. You have verified that all data to be submitted is accurate and complete")
    print_info("3. You understand that existing entries may be overwritten without recovery")
    print_info("4. This tool is provided as-is with no warranty or guarantees of any kind")
    print_info("5. The developers are not responsible for any issues arising from its use")
    
    print_info("\nDo you accept these terms and wish to continue? (y/n):")
    if input().strip().lower() != 'y':
        print_warning("You must accept the disclaimer to use this tool. Exiting...")
        sys.exit(1)
    
    cookies = load_cookies()
    if not cookies:
        print_info("No saved session found. Logging in...")
        username, password = get_credentials()
        login(username=username, password=password)
        cookies = load_cookies()
        if not cookies:
            print_error("Failed to log in. Please try again.")
            return
    else:
        print_success("Using existing cookies...")
    
    process_csv_input()

if __name__ == "__main__":
    main()
