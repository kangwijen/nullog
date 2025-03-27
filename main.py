from cookies import load_cookies
from login import login
from api import submit_logbook, get_logbook_months, get_logbook_entries, is_date_filled
from config import get_credentials
from datetime import datetime

def get_user_input():
    while True:
        try:
            print("Start date (1-31):")
            start = int(input())
            if not 1 <= start <= 31:
                print("Start date must be between 1 and 31")
                continue
                
            print("End Date (1-31):")
            end = int(input())
            if not 1 <= end <= 31 or end < start:
                print("End date must be between 1 and 31 and greater than or equal to start date")
                continue
                
            current_date = datetime.now()
            year = current_date.year
            month = current_date.month
            
            print("Clock in (0-24):")
            clock_in = int(input())
            if not 0 <= clock_in <= 24:
                print("Clock in must be between 0 and 24")
                continue
                
            print("Clock out (0-24):")
            clock_out = int(input())
            if not 0 <= clock_out <= 24 or clock_out <= clock_in:
                print("Clock out must be between 0 and 24 and greater than clock in")
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
                
            clock_in_str = f"{clock_in % 12 or 12}:00 {'am' if clock_in < 12 else 'pm'}"
            clock_out_str = f"{clock_out % 12 or 12}:00 {'am' if clock_out < 12 else 'pm'}"
            
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

if __name__ == "__main__":
    cookies = load_cookies()
    if not cookies:
        username, password = get_credentials()
        login(username=username, password=password)
        cookies = load_cookies()
    else:
        print("Using existing cookies...")
    
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
    for day in range(user_input['start_date'], user_input['end_date'] + 1):
        try:
            date_obj = datetime(user_input['year'], user_input['month'], day)
            dates.append(date_obj.strftime('%Y-%m-%d'))
        except ValueError:
            print(f"Invalid date: {user_input['year']}-{user_input['month']}-{day}, skipping...")
    
    for target_date in dates:
        date_obj = datetime.strptime(target_date, '%Y-%m-%d')
        weekday = date_obj.weekday()
        
        if weekday == 6:
            print(f"Skipping Sunday: {target_date}")
            continue
        
        if is_date_filled(existing_entries, target_date):
            print(f"Entry already exists for {target_date}, skipping...")
            continue
            
        print(f"Submitting logbook for date: {target_date}")
        
        if weekday == 5:
            print(f"Saturday detected - submitting as OFF day")
            response = submit_logbook(
                date=target_date,
                activity="OFF",
                clock_in="OFF",
                clock_out="OFF",
                description="OFF"
            )
        else:
            response = submit_logbook(
                date=target_date,
                activity=user_input['activity'],
                clock_in=user_input['clock_in'],
                clock_out=user_input['clock_out'],
                description=user_input['description']
            )
        
        print(f"Logbook submission response: {response}")
