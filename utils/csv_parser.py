import csv
from datetime import datetime
import os
import sys
from utils.utils import is_valid_time_format, logger
from utils.constants import WEEKDAY_SUNDAY
from utils.display import print_error, print_warning, print_info, print_success, display_csv_entries

def validate_date(row_num, date_str):
    try:
        if not date_str or not isinstance(date_str, str):
            error_msg = f"Empty or invalid date in row {row_num}"
            logger.error(error_msg)
            return None, None, error_msg
            
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
            if date > datetime.now():
                error_msg = f"Future date '{date_str}' in row {row_num} is not allowed"
                logger.error(error_msg)
                return None, None, error_msg
            logger.debug(f"Date validation passed for row {row_num}: {date_str}")
            return date.strftime('%Y-%m-%d'), date.weekday(), None
        except ValueError as e:
            error_msg = f"Invalid date format '{date_str}' in row {row_num}. Use YYYY-MM-DD format. Error: {str(e)}"
            logger.error(error_msg)
            return None, None, error_msg
    except Exception as e:
        error_msg = f"Unexpected error validating date '{date_str}' in row {row_num}: {str(e)}"
        logger.error(error_msg)
        return None, None, error_msg

def validate_time_fields(row_num, row):
    try:
        for time_field in ['clock_in', 'clock_out']:
            if time_field not in row:
                error_msg = f"Missing time field '{time_field}' in row {row_num}"
                logger.error(error_msg)
                return False, error_msg
            
            time_val = row[time_field].strip()
            if not is_valid_time_format(time_val):
                error_msg = f"Invalid time format '{time_val}' in row {row_num}, column {time_field}. Use HH:MM format (24-hour) or OFF."
                logger.error(error_msg)
                return False, error_msg
        
        # Validate clock out is after clock in
        if row['clock_in'] != "OFF" and row['clock_out'] != "OFF":
            try:
                clock_in_hour, clock_in_min = map(int, row['clock_in'].split(':'))
                clock_out_hour, clock_out_min = map(int, row['clock_out'].split(':'))
                if (clock_out_hour < clock_in_hour) or (clock_out_hour == clock_in_hour and clock_out_min <= clock_in_min):
                    error_msg = f"Error in row {row_num}: Clock out time ({row['clock_out']}) must be later than clock in time ({row['clock_in']})"
                    logger.error(error_msg)
                    return False, error_msg
            except ValueError as e:
                error_msg = f"Error parsing time values in row {row_num}: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
        
        logger.debug(f"Time validation passed for row {row_num}")
        return True, None
    except Exception as e:
        error_msg = f"Unexpected error validating time fields in row {row_num}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def parse_csv_file(filepath):
    entries = []
    errors = []
    sundays = []
    row_count = 0
    error_count = 0
    processed_dates = set()
    
    try:
        logger.info(f"Starting CSV file parsing: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            required_fields = ['date', 'activity', 'clock_in', 'clock_out', 'description']
            header = reader.fieldnames
            
            if not header:
                error_msg = "CSV file has no headers"
                logger.error(error_msg)
                errors.append(error_msg)
                return None, errors
                
            missing_headers = [f for f in required_fields if f not in header]
            if missing_headers:
                error_msg = f"CSV file is missing required headers: {', '.join(missing_headers)}"
                logger.error(error_msg)
                errors.append(error_msg)
                return None, errors
            
            logger.info(f"CSV headers validated: {header}")
            
            for row_num, row in enumerate(reader, 2):
                row_count += 1
                if error_count >= 5:
                    error_msg = f"Too many errors ({error_count}). Aborting CSV import."
                    logger.error(error_msg)
                    errors.append(error_msg)
                    return None, errors
                    
                # Skip empty rows
                if all(not val.strip() if val else True for val in row.values()):
                    logger.debug(f"Skipping empty row {row_num}")
                    continue
                    
                # Check for missing fields
                if not all(field in row for field in required_fields):
                    missing = [f for f in required_fields if f not in row]
                    error_msg = f"Missing fields in CSV row {row_num}: {', '.join(missing)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    error_count += 1
                    continue
                
                # Check for empty required fields
                empty_fields = [f for f in required_fields if f in row and not row[f].strip()]
                if empty_fields:
                    error_msg = f"Empty required fields in row {row_num}: {', '.join(empty_fields)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    error_count += 1
                    continue
                
                # Validate date
                formatted_date, weekday, date_error = validate_date(row_num, row['date'])
                if date_error:
                    errors.append(date_error)
                    error_count += 1
                    continue
                    
                # Check for duplicate dates
                if formatted_date in processed_dates:
                    error_msg = f"Duplicate date '{formatted_date}' in row {row_num}. Each date must be unique."
                    logger.error(error_msg)
                    errors.append(error_msg)
                    error_count += 1
                    continue
                
                processed_dates.add(formatted_date)
                row['date'] = formatted_date
                
                # Validate OFF consistency
                off_fields = ['activity', 'clock_in', 'clock_out', 'description']
                is_any_off = any(row[field].strip() == "OFF" for field in off_fields)
                all_off = all(row[field].strip() == "OFF" for field in off_fields)
                
                if is_any_off and not all_off:
                    non_off_fields = [f for f in off_fields if row[f].strip() != "OFF"]
                    error_msg = f"Inconsistent OFF values in row {row_num}. When any field is 'OFF', all fields (activity, clock_in, clock_out, description) must be 'OFF'. Fields not set to 'OFF': {', '.join(non_off_fields)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    error_count += 1
                    continue
                
                # Skip Sundays
                if weekday == WEEKDAY_SUNDAY:
                    logger.info(f"Sunday entry found in row {row_num}: {formatted_date}")
                    sundays.append((row_num, row['date']))
                    continue
                
                # Validate time fields
                valid_time, time_error = validate_time_fields(row_num, row)
                if not valid_time:
                    errors.append(time_error)
                    error_count += 1
                    continue
                
                entries.append(row)
                logger.debug(f"Successfully processed row {row_num}: {formatted_date}")
        
        logger.info(f"CSV parsing completed: {len(entries)} valid entries, {len(errors)} errors, {len(sundays)} Sundays")
        
        if not entries:
            if row_count == 0:
                error_msg = "CSV file is empty"
                logger.error(error_msg)
                errors.append(error_msg)
            elif len(sundays) == row_count:
                error_msg = "CSV file contains only Sunday entries which will be skipped"
                logger.warning(error_msg)
                errors.append(error_msg)
            else:
                error_msg = "No valid entries found in CSV file after validation"
                logger.error(error_msg)
                errors.append(error_msg)
            return None, errors
        
        if sundays:
            sunday_warnings = []
            sunday_warnings.append("\nThe following Sunday entries were found in your CSV and will be skipped:")
            for row_num, date in sundays:
                sunday_warnings.append(f"  - Row {row_num}: {date} (Sunday)")
            errors.extend(sunday_warnings)
            
        return entries, errors
        
    except FileNotFoundError:
        error_msg = f"File not found: {filepath}"
        logger.error(error_msg)
        errors.append(error_msg)
        return None, errors
    except PermissionError:
        error_msg = f"Permission denied when accessing file: {filepath}"
        logger.error(error_msg)
        errors.append(error_msg)
        return None, errors
    except UnicodeDecodeError as e:
        error_msg = f"Unicode decode error reading CSV file: {str(e)}. Try saving the file with UTF-8 encoding."
        logger.error(error_msg)
        errors.append(error_msg)
        return None, errors
    except csv.Error as e:
        error_msg = f"CSV parsing error: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        return None, errors
    except Exception as e:
        error_msg = f"Unexpected error reading CSV file: {e}"
        logger.error(error_msg)
        errors.append(error_msg)
        return None, errors

def import_from_csv():
    max_attempts = 3
    attempts = 0
    
    logger.info("Starting CSV import process")
    
    while attempts < max_attempts:
        try:
            attempts += 1
            logger.info(f"CSV import attempt {attempts}/{max_attempts}")
            
            print_info(f"Enter CSV file path:")
            filepath = input().strip()
            
            if not filepath:
                logger.warning("Empty file path provided")
                print_error("File path cannot be empty")
                continue
                
            if not os.path.exists(filepath):
                logger.warning(f"File not found: {filepath}")
                print_error(f"File not found: {filepath}")
                continue
                
            if not os.path.isfile(filepath):
                logger.warning(f"Not a valid file: {filepath}")
                print_error(f"Not a valid file: {filepath}")
                continue
                
            logger.info(f"Processing CSV file: {filepath}")
            entries, errors = parse_csv_file(filepath)
            
            if not entries:
                logger.error("Failed to parse CSV file")
                print_error("Failed to parse CSV file. Please check the format and try again.")
                # We'll display detailed errors later in main.py
                continue
                
            logger.info(f"Successfully loaded {len(entries)} entries from CSV")
            print_success(f"Successfully loaded {len(entries)} entries from CSV.")
            return entries, errors
            
        except KeyboardInterrupt:
            logger.info("CSV import cancelled by user")
            print_warning("\nCSV import cancelled by user.")
            sys.exit(0)
        except Exception as e:
            logger.error(f"Unexpected error during CSV import: {str(e)}")
            print_error(f"Error: {e}")
    
    logger.error(f"Failed after {max_attempts} attempts")
    print_error(f"Failed after {max_attempts} attempts. Exiting.")
    sys.exit(1)