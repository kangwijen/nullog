import csv
from datetime import datetime
import os
import sys
from utils import is_valid_time_format
from constants import WEEKDAY_SUNDAY
from display import print_error, print_warning, print_info, print_success, display_csv_entries

def validate_date(row_num, date_str):
    if not date_str or not isinstance(date_str, str):
        print_error(f"Empty or invalid date in row {row_num}")
        return None, None
        
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d')
        if date > datetime.now():
            print_error(f"Future date '{date_str}' in row {row_num} is not allowed")
            return None, None
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
    entries = []
    sundays = []
    row_count = 0
    error_count = 0
    processed_dates = set()
    
    try:
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            
            required_fields = ['date', 'activity', 'clock_in', 'clock_out', 'description']
            header = reader.fieldnames
            
            if not header:
                print_error("CSV file has no headers")
                return None
                
            missing_headers = [f for f in required_fields if f not in header]
            if missing_headers:
                print_error(f"CSV file is missing required headers: {', '.join(missing_headers)}")
                return None
            
            for row_num, row in enumerate(reader, 2):
                row_count += 1
                if error_count >= 5:
                    print_error(f"Too many errors ({error_count}). Aborting CSV import.")
                    return None
                    
                if all(not val.strip() if val else True for val in row.values()):
                    continue
                    
                if not all(field in row for field in required_fields):
                    missing = [f for f in required_fields if f not in row]
                    print_error(f"Missing fields in CSV row {row_num}: {', '.join(missing)}")
                    error_count += 1
                    continue
                
                empty_fields = [f for f in required_fields if f in row and not row[f].strip()]
                if empty_fields:
                    print_error(f"Empty required fields in row {row_num}: {', '.join(empty_fields)}")
                    error_count += 1
                    continue
                
                formatted_date, weekday = validate_date(row_num, row['date'])
                if formatted_date is None:
                    error_count += 1
                    continue
                    
                if formatted_date in processed_dates:
                    print_error(f"Duplicate date '{formatted_date}' in row {row_num}. Each date must be unique.")
                    error_count += 1
                    continue
                
                processed_dates.add(formatted_date)
                row['date'] = formatted_date
                
                if weekday == WEEKDAY_SUNDAY:
                    sundays.append((row_num, row['date']))
                    continue
                
                if not validate_time_fields(row_num, row):
                    error_count += 1
                    continue
                
                entries.append(row)
        
        if not entries:
            if row_count == 0:
                print_error("CSV file is empty")
            elif len(sundays) == row_count:
                print_error("CSV file contains only Sunday entries which will be skipped")
            else:
                print_error("No valid entries found in CSV file after validation")
            return None
        
        if sundays:
            print_warning("\nThe following Sunday entries were found in your CSV and will be skipped:")
            for row_num, date in sundays:
                print_warning(f"  - Row {row_num}: {date} (Sunday)")
            print("")
            
        return entries
    except FileNotFoundError:
        print_error(f"File not found: {filepath}")
        return None
    except PermissionError:
        print_error(f"Permission denied when accessing file: {filepath}")
        return None
    except csv.Error as e:
        print_error(f"CSV parsing error: {e}")
        return None
    except Exception as e:
        print_error(f"Unexpected error reading CSV file: {e}")
        return None

def import_from_csv():
    max_attempts = 3
    attempts = 0
    
    while attempts < max_attempts:
        try:
            attempts += 1
            print_info(f"Enter CSV file path:")
            filepath = input().strip()
            
            if not filepath:
                print_error("File path cannot be empty")
                continue
                
            if not os.path.exists(filepath):
                print_error(f"File not found: {filepath}")
                continue
                
            if not os.path.isfile(filepath):
                print_error(f"Not a valid file: {filepath}")
                continue
                
            entries = parse_csv_file(filepath)
            if not entries:
                print_error("Failed to parse CSV file. Please check the format and try again.")
                continue
                
            print_success(f"Successfully loaded {len(entries)} entries from CSV.")
            return entries
            
        except KeyboardInterrupt:
            print_warning("\nCSV import cancelled by user.")
            sys.exit(0)
        except Exception as e:
            print_error(f"Error: {e}")
    
    print_error(f"Failed after {max_attempts} attempts. Exiting.")
    sys.exit(1)