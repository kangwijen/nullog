import csv
from datetime import datetime
import os

def parse_csv_file(filepath):
    entries = []
    sundays = []
    try:
        with open(filepath, 'r') as file:
            reader = csv.DictReader(file)
            for row_num, row in enumerate(reader, 2):
                required_fields = ['date', 'activity', 'clock_in', 'clock_out', 'description']
                if not all(field in row for field in required_fields):
                    missing = [f for f in required_fields if f not in row]
                    print(f"Error: Missing fields in CSV row {row_num}: {', '.join(missing)}")
                    return None
                
                try:
                    date = datetime.strptime(row['date'], '%Y-%m-%d')
                    row['date'] = date.strftime('%Y-%m-%d')
                    
                    if date.weekday() == 6:
                        sundays.append((row_num, row['date']))
                        continue
                except ValueError:
                    print(f"Error: Invalid date format '{row['date']}' in row {row_num}. Use YYYY-MM-DD format.")
                    return None
                
                for time_field in ['clock_in', 'clock_out']:
                    time_val = row[time_field].strip()
                    if time_val != "OFF":
                        if not (len(time_val) == 5 and time_val[2] == ':' and 
                                time_val[:2].isdigit() and time_val[3:].isdigit() and
                                0 <= int(time_val[:2]) <= 23 and 0 <= int(time_val[3:]) <= 59):
                            print(f"Error: Invalid time format '{time_val}' in row {row_num}, column {time_field}. Use HH:MM format (24-hour).")
                            return None
                
                if row['clock_in'] != "OFF" and row['clock_out'] != "OFF":
                    clock_in_hour, clock_in_min = map(int, row['clock_in'].split(':'))
                    clock_out_hour, clock_out_min = map(int, row['clock_out'].split(':'))
                    if (clock_out_hour < clock_in_hour) or (clock_out_hour == clock_in_hour and clock_out_min <= clock_in_min):
                        print(f"Error in row {row_num}: Clock out time ({row['clock_out']}) must be later than clock in time ({row['clock_in']})")
                        return None
                
                entries.append(row)
                
        if not entries:
            print("Error: CSV file is empty or contains only Sunday entries")
            return None
        
        if sundays:
            print("\nNote: The following Sunday entries were found in your CSV and will be skipped:")
            for row_num, date in sundays:
                print(f"  - Row {row_num}: {date} (Sunday)")
            print("")
            
        return entries
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return None

def import_from_csv():
    while True:
        try:
            print("Enter CSV file path:")
            filepath = input().strip()
            
            if not filepath:
                print("File path cannot be empty")
                continue
                
            if not os.path.exists(filepath):
                print(f"File not found: {filepath}")
                continue
                
            entries = parse_csv_file(filepath)
            if not entries:
                print("Failed to parse CSV file. Please check the format and try again.")
                continue
                
            print(f"Successfully loaded {len(entries)} entries from CSV.")
            return entries
            
        except Exception as e:
            print(f"Error: {e}")