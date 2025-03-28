import csv
from datetime import datetime
import os
from utils import is_valid_time_format
from constants import WEEKDAY_SUNDAY
from display import print_error, print_warning, print_info, print_success, display_csv_entries

def validate_date(row_num, date_str):
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        return date.strftime('%Y-%m-%d'), date.weekday()
    except ValueError:
        print_error(f"Invalid date format '{date_str}' in row {row_num}. Use YYYY-MM-DD format.")
        return None, None

def validate_time_fields(row_num, row):
    for time_field in ['clock_in', 'clock_out']:
        time_val = row[time_field].strip()
        if not is_valid_time_format(time_val):
            print_error(f"Invalid time format '{time_val}' in row {row_num}, column {time_field}. Use HH:MM format (24-hour) or OFF.")
            return False
    
    if row['clock_in'] != "OFF" and row['clock_out'] != "OFF":
        clock_in_hour, clock_in_min = map(int, row['clock_in'].split(':'))
        clock_out_hour, clock_out_min = map(int, row['clock_out'].split(':'))
        if (clock_out_hour < clock_in_hour) or (clock_out_hour == clock_in_hour and clock_out_min <= clock_in_min):
            print_error(f"Error in row {row_num}: Clock out time ({row['clock_out']}) must be later than clock in time ({row['clock_in']})")
            return False
    
    return True

def parse_csv_file(filepath):
    """Parse a CSV file with logbook entries."""
    entries = []
    sundays = []
    
    try:
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            for row_num, row in enumerate(reader, 2):
                required_fields = ['date', 'activity', 'clock_in', 'clock_out', 'description']
                if not all(field in row for field in required_fields):
                    missing = [f for f in required_fields if f not in row]
                    print_error(f"Missing fields in CSV row {row_num}: {', '.join(missing)}")
                    return None
                
                formatted_date, weekday = validate_date(row_num, row['date'])
                if formatted_date is None:
                    return None
                    
                row['date'] = formatted_date
                
                if weekday == WEEKDAY_SUNDAY:
                    sundays.append((row_num, row['date']))
                    continue
                
                if not validate_time_fields(row_num, row):
                    return None
                
                entries.append(row)
        
        if not entries:
            print_error("CSV file is empty or contains only Sunday entries")
            return None
        
        if sundays:
            print_warning("\nThe following Sunday entries were found in your CSV and will be skipped:")
            for row_num, date in sundays:
                print_warning(f"  - Row {row_num}: {date} (Sunday)")
            print("")
            
        return entries
    except Exception as e:
        print_error(f"Error reading CSV file: {e}")
        return None

def import_from_csv():
    while True:
        try:
            print_info("Enter CSV file path:")
            filepath = input().strip()
            
            if not filepath:
                print_error("File path cannot be empty")
                continue
                
            if not os.path.exists(filepath):
                print_error(f"File not found: {filepath}")
                continue
                
            entries = parse_csv_file(filepath)
            if not entries:
                print_error("Failed to parse CSV file. Please check the format and try again.")
                continue
                
            print_success(f"Successfully loaded {len(entries)} entries from CSV.")
            return entries
            
        except Exception as e:
            print_error(f"Error: {e}")