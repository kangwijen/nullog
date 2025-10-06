from colorama import init, Fore, Style
from tabulate import tabulate
from datetime import datetime

init(autoreset=True)

def print_success(message):
    print(f"{Fore.GREEN}{message}{Style.RESET_ALL}")

def print_error(message):
    print(f"{Fore.RED}{message}{Style.RESET_ALL}")

def print_warning(message):
    print(f"{Fore.YELLOW}{message}{Style.RESET_ALL}")

def print_info(message):
    print(f"{Fore.CYAN}{message}{Style.RESET_ALL}")

def print_header(message):
    print(f"\n{Fore.BLUE}{Style.BRIGHT}{message}{Style.RESET_ALL}")

def print_table(data, headers, title=None):
    if title:
        print_header(title)
    print(tabulate(data, headers=headers, tablefmt="grid"))
    print()

def format_logbook_entries(entries):
    if not entries or "data" not in entries or not entries["data"]:
        return []
    
    table_data = []
    for entry in entries["data"]:
        if entry["id"] != "00000000-0000-0000-0000-000000000000" and entry["clockIn"]:
            date_str = entry["date"].split("T")[0] if "T" in entry["date"] else entry["date"]
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%d %b %Y')
            except ValueError:
                formatted_date = date_str
                
            table_data.append([
                formatted_date,
                entry["activity"],
                entry["clockIn"],
                entry["clockOut"],
                entry["description"]
            ])
    
    return table_data

def display_csv_entries(entries):
    if not entries:
        print_warning("No entries to display")
        return
        
    table_data = []
    for entry in entries:
        try:
            date_obj = datetime.strptime(entry['date'], '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d %b %Y')
        except ValueError:
            formatted_date = entry['date']
            
        table_data.append([
            formatted_date,
            entry['activity'],
            entry['clock_in'],
            entry['clock_out'],
            entry['description']
        ])
    
    print_table(
        table_data,
        ["Date", "Activity", "Clock In", "Clock Out", "Description"],
        "CSV Entries to Submit"
    )

def display_available_months(completion_status):
    table_data = []
    prev_complete = True
    blocked = False

    sorted_months = sorted(
        completion_status.items(),
        key=lambda x: (x[1]['year'], x[0])
    )

    for month, status in sorted_months:
        if blocked or not prev_complete:
            completion_indicator = "✗"
            color = Fore.RED
            empty_status = "Unfilled"
            submit_status = "Unsubmitted"
            availability = "BLOCKED - Complete previous month first"
            avail_color = Fore.RED
            blocked = True
        else:
            completion_indicator = "✓" if status['completed'] else "✗"
            color = Fore.GREEN if status['completed'] else Fore.RED
            empty_status = f"{status['empty_entries']} unfilled" if status['empty_entries'] > 0 else "All filled"
            
            submitted_count = status.get('filledSubmit', 0)
            filled_total = status.get('filledAll', status.get('filled_entries', 0))
            submit_status = f"{submitted_count}/{filled_total} submitted"
            
            availability = "Available"
            avail_color = Fore.GREEN

        table_data.append([
            month,
            status['month_name'],
            status['year'],
            f"{color}{completion_indicator}{Style.RESET_ALL}",
            empty_status,
            submit_status,
            f"{avail_color}{availability}{Style.RESET_ALL}"
        ])

        prev_complete = status['completed'] and not blocked

    print_table(
        table_data,
        ["Month #", "Month", "Year", "Complete", "Fill Status", "Submit Status", "Availability"],
        "Available Months in Logbook"
    )
