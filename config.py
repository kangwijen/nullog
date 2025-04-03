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
