from cookies import load_cookies
from login import login
from api import submit_logbook, get_logbook_months, get_logbook_entries, is_date_filled
from config import get_credentials
from datetime import datetime
from csv_parser import import_from_csv

def get_user_input():
    while True:
        try:
            current_date = datetime.now()
            year = current_date.year
            month = current_date.month
            current_day = current_date.day
            
            print("Start date (1-31):")
            start = int(input())
            if not 1 <= start <= 31:
                print("Start date must be between 1 and 31")
                continue
            
            if year == current_date.year and month == current_date.month and start > current_day:
                print("Start date cannot be in the future")
                continue
                
            print("End Date (1-31):")
            end = int(input())
            if not 1 <= end <= 31 or end < start:
                print("End date must be between 1 and 31 and greater than or equal to start date")
                continue
            
            if year == current_date.year and month == current_date.month and end > current_day:
                print("End date cannot be in the future")
                continue
            
            print("Clock in time (24-hour format, e.g. 09:00 or OFF):")
            clock_in = input().strip()
            if clock_in != "OFF" and not (len(clock_in) == 5 and clock_in[2] == ':' and 
                    clock_in[:2].isdigit() and clock_in[3:].isdigit() and
                    0 <= int(clock_in[:2]) <= 23 and 0 <= int(clock_in[3:]) <= 59):
                print("Clock in must be in format HH:MM (24-hour) or OFF")
                continue
                
            print("Clock out time (24-hour format, e.g. 18:00 or OFF):")
            clock_out = input().strip()
            if clock_out != "OFF" and not (len(clock_out) == 5 and clock_out[2] == ':' and 
                    clock_out[:2].isdigit() and clock_out[3:].isdigit() and
                    0 <= int(clock_out[:2]) <= 23 and 0 <= int(clock_out[3:]) <= 59):
                print("Clock out must be in format HH:MM (24-hour) or OFF")
                continue
            
            if clock_in != "OFF" and clock_out != "OFF":
                clock_in_hour, clock_in_min = map(int, clock_in.split(':'))
                clock_out_hour, clock_out_min = map(int, clock_out.split(':'))
                if (clock_out_hour < clock_in_hour) or (clock_out_hour == clock_in_hour and clock_out_min <= clock_in_min):
                    print("Clock out time must be later than clock in time")
                    continue
                
            print("Activity: ")
            activity = input()
            if not activity:
                print("Activity cannot be empty")
                continue
                
            print("Description: ")
            description = input()
            if not description:
                print("Description cannot be empty")
                continue
            
            clock_in_str = clock_in
            clock_out_str = clock_out
            
            return {
                'start_date': start,
                'end_date': end,
                'year': year,
                'month': month,
                'activity': activity,
                'clock_in': clock_in_str,
                'clock_out': clock_out_str,
                'description': description
            }
        except ValueError:
            print("Please enter valid numbers for dates and times")

def process_single_day(date, activity, clock_in, clock_out, description, existing_entries):
    date_obj = datetime.strptime(date, '%Y-%m-%d')
    weekday = date_obj.weekday()
    
    if weekday == 6:
        print(f"Skipping Sunday: {date}")
        return
    
    if is_date_filled(existing_entries, date):
        print(f"Entry already exists for {date}, skipping...")
        return
        
    print(f"Submitting logbook for date: {date}")
    
    if weekday == 5:
        print(f"Saturday detected - submitting as OFF day")
        response = submit_logbook(
            date=date,
            activity="OFF",
            clock_in="OFF",
            clock_out="OFF",
            description="OFF"
        )
    else:
        response = submit_logbook(
            date=date,
            activity=activity,
            clock_in=clock_in,
            clock_out=clock_out,
            description=description
        )
    
    print(f"Logbook submission response: {response}")

if __name__ == "__main__":
    cookies = load_cookies()
    if not cookies:
        username, password = get_credentials()
        login(username=username, password=password)
        cookies = load_cookies()
    else:
        print("Using existing cookies...")
    
    print("Choose input method:")
    print("1. Manual input (single activity for multiple days)")
    print("2. Import from CSV (different activities for different days)")
    
    option = input().strip()
    
    if option == "1":
        user_input = get_user_input()
        
        month_mapping = get_logbook_months()
        current_month = user_input['month']
        
        if current_month in month_mapping:
            logbook_header_id = month_mapping[current_month]
            print(f"Using LogBookHeaderID {logbook_header_id} for month {current_month}")
            
            existing_entries = get_logbook_entries(logbook_header_id)
            if "error" in existing_entries:
                print(f"Error fetching existing entries: {existing_entries['error']}")
                exit(1)
        else:
            print(f"No LogBookHeaderID found for month {current_month}. Cannot proceed.")
            exit(1)
        
        dates = []
        sundays = []
        for day in range(user_input['start_date'], user_input['end_date'] + 1):
            try:
                date_obj = datetime(user_input['year'], user_input['month'], day)
                date_str = date_obj.strftime('%Y-%m-%d')
                
                if date_obj.weekday() == 6:
                    sundays.append(date_str)
                else:
                    dates.append(date_str)
            except ValueError:
                print(f"Invalid date: {user_input['year']}-{user_input['month']}-{day}, skipping...")
        
        if sundays:
            print("\nNote: The following Sundays in your date range will be skipped:")
            for sunday in sundays:
                print(f"  - {sunday}")
            print("")
        
        for target_date in dates:
            process_single_day(
                date=target_date,
                activity=user_input['activity'],
                clock_in=user_input['clock_in'],
                clock_out=user_input['clock_out'],
                description=user_input['description'],
                existing_entries=existing_entries
            )
            
    elif option == "2":
        csv_entries = import_from_csv()
        if not csv_entries:
            print("No valid entries found in CSV. Exiting.")
            exit(1)
        
        entries_by_month = {}
        for entry in csv_entries:
            date_obj = datetime.strptime(entry['date'], '%Y-%m-%d')
            month = date_obj.month
            year = date_obj.year
            month_key = (year, month)
            if month_key not in entries_by_month:
                entries_by_month[month_key] = []
            entries_by_month[month_key].append(entry)
        
        month_mapping = get_logbook_months()
        
        for (year, month), entries in entries_by_month.items():
            if month in month_mapping:
                logbook_header_id = month_mapping[month]
                print(f"Using LogBookHeaderID {logbook_header_id} for month {month}/{year}")
                
                existing_entries = get_logbook_entries(logbook_header_id)
                if "error" in existing_entries:
                    print(f"Error fetching existing entries for month {month}/{year}: {existing_entries['error']}")
                    continue
                
                for entry in entries:
                    process_single_day(
                        date=entry['date'],
                        activity=entry['activity'],
                        clock_in=entry['clock_in'],
                        clock_out=entry['clock_out'],
                        description=entry['description'],
                        existing_entries=existing_entries
                    )
            else:
                print(f"No LogBookHeaderID found for month {month}/{year}. Skipping entries for this month.")
    else:
        print("Invalid option. Please choose 1 or 2.")
