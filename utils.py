import os
import json
import base64
import logging
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from constants import COOKIES_DIR, COOKIES_FILE, DEFAULT_USER_AGENT

# Configure logging
def setup_logging(log_level=logging.INFO):
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    
    # Setup console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)  # Only show warnings and errors in console
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logger
logger = setup_logging()

def get_cookies_path():
    cookies_dir = os.path.join(os.path.dirname(__file__), COOKIES_DIR)
    os.makedirs(cookies_dir, exist_ok=True)
    return os.path.join(cookies_dir, COOKIES_FILE)

def get_key_file_path():
    cookies_dir = os.path.join(os.path.dirname(__file__), COOKIES_DIR)
    os.makedirs(cookies_dir, exist_ok=True)
    return os.path.join(cookies_dir, "key.bin")

def derive_key_from_password(password, salt=None):
    try:
        if salt is None:
            salt = os.urandom(16)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        logger.debug("Successfully derived encryption key from password")
        return key, salt
    except Exception as e:
        logger.error(f"Failed to derive encryption key: {str(e)}")
        raise

def get_or_create_key():
    key_file = get_key_file_path()
    
    if os.path.exists(key_file):
        try:
            with open(key_file, 'rb') as f:
                key_data = f.read()
                salt = key_data[:16]
                key = key_data[16:]
            logger.info("Loaded existing encryption key")
            return key, salt
        except Exception as e:
            logger.warning(f"Failed to load existing key file: {str(e)}")
            # If key file is corrupted, create new one
            pass
    
    # Create new key
    logger.info("Creating new encryption key")
    password = input("Enter a password to encrypt your session data (or press Enter for default): ").strip()
    if not password:
        password = "nullog_default_password"
        logger.info("Using default password for encryption")
    
    key, salt = derive_key_from_password(password)
    
    # Save key
    try:
        with open(key_file, 'wb') as f:
            f.write(salt + key)
        logger.info("Encryption key saved successfully")
    except Exception as e:
        logger.error(f"Failed to save encryption key: {str(e)}")
        raise
    
    return key, salt

def save_data_securely(data):
    try:
        cookies_path = get_cookies_path()
        key, salt = get_or_create_key()
        
        fernet = Fernet(key)
        encrypted_data = fernet.encrypt(json.dumps(data).encode())
        
        with open(cookies_path, "wb") as f:
            f.write(encrypted_data)
        
        logger.info(f"Data securely saved to {cookies_path}")
        print(f"Data securely saved to {cookies_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving data securely: {str(e)}")
        print(f"Error saving data securely: {str(e)}")
        return False

def load_data_securely():
    try:
        cookies_path = get_cookies_path()
        if not os.path.exists(cookies_path):
            logger.info("No encrypted data file found")
            return None
        
        key, salt = get_or_create_key()
        fernet = Fernet(key)
        
        with open(cookies_path, "rb") as f:
            encrypted_data = f.read()
        
        decrypted_data = fernet.decrypt(encrypted_data)
        data = json.loads(decrypted_data.decode())
        logger.info("Successfully loaded encrypted data")
        return data
    except Exception as e:
        logger.error(f"Error loading data securely: {str(e)}")
        print(f"Error loading data securely: {str(e)}")
        return None

# Legacy support - will be removed in future versions
def save_data_to_pickle(data):
    """Legacy function - now uses secure storage"""
    logger.warning("Using legacy save_data_to_pickle function - consider updating to save_data_securely")
    return save_data_securely(data)

def load_data_from_pickle():
    """Legacy function - now uses secure storage"""
    logger.warning("Using legacy load_data_from_pickle function - consider updating to load_data_securely")
    return load_data_securely()

def is_valid_time_format(time_str):
    try:
        if time_str == "OFF":
            return True
        
        if (len(time_str) == 5 and time_str[2] == ':' and 
                time_str[:2].isdigit() and time_str[3:].isdigit() and
                0 <= int(time_str[:2]) <= 23 and 0 <= int(time_str[3:]) <= 59):
            return True
        
        logger.debug(f"Invalid time format: {time_str}")
        return False
    except Exception as e:
        logger.error(f"Error validating time format '{time_str}': {str(e)}")
        return False

def convert_12hour(time_str):
    try:
        if time_str == "OFF":
            return "OFF"
        
        hour, minute = map(int, time_str.split(':'))
        
        period = "am" if hour < 12 else "pm"
        
        if hour == 0:
            hour = 12
        elif hour > 12:
            hour -= 12
        
        result = f"{hour:02d}:{minute:02d} {period}"
        logger.debug(f"Converted {time_str} to {result}")
        return result
    except Exception as e:
        logger.error(f"Error converting time format '{time_str}': {str(e)}")
        return time_str

def format_iso_date(date_obj):
    try:
        if isinstance(date_obj, str):
            date_obj = datetime.strptime(date_obj, '%Y-%m-%d')
        
        result = f"{date_obj.strftime('%Y-%m-%d')}T00:00:00"
        logger.debug(f"Formatted date {date_obj} to {result}")
        return result
    except Exception as e:
        logger.error(f"Error formatting date {date_obj}: {str(e)}")
        return str(date_obj)
