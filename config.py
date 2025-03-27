import os
from dotenv import load_dotenv
import getpass

load_dotenv()

def get_credentials():
    username = os.getenv("USER_EMAIL_NLG")
    password = os.getenv("USER_PASSWORD_NLG")
    
    if not username:
        username = input("Enter email: ")
    if not password:
        password = getpass.getpass("Enter password: ")
    
    return username, password

def get_logbook_defaults():
    return {
        "activity": os.getenv("DEFAULT_ACTIVITY", "Self Study"),
        "clock_in": os.getenv("DEFAULT_CLOCK_IN", "09:00 am"),
        "clock_out": os.getenv("DEFAULT_CLOCK_OUT", "06:00 pm"),
        "description": os.getenv("DEFAULT_DESCRIPTION", "Self study activities")
    }
