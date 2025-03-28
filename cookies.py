from utils import load_data_from_pickle
from constants import DEFAULT_USER_AGENT

def load_cookies():
    data = load_data_from_pickle()
    
    if data:
        if isinstance(data, dict) and "cookies" in data:
            return data["cookies"]
        else:
            return data
    else:
        print("No saved cookies found.")
        return None

def load_user_agent():
    data = load_data_from_pickle()
    
    if data and isinstance(data, dict) and "user_agent" in data:
        return data["user_agent"]
    
    return DEFAULT_USER_AGENT