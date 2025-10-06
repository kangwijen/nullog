from utils import load_data_securely, logger
from constants import DEFAULT_USER_AGENT

def load_cookies():
    try:
        data = load_data_securely()
        
        if data:
            if isinstance(data, dict) and "cookies" in data:
                logger.info("Successfully loaded cookies from secure storage")
                return data["cookies"]
            else:
                logger.warning("Data format is not as expected, returning raw data")
                return data
        else:
            logger.info("No saved cookies found in secure storage")
            print("No saved cookies found.")
            return None
    except Exception as e:
        logger.error(f"Error loading cookies: {str(e)}")
        print(f"Error loading cookies: {str(e)}")
        return None

def load_user_agent():
    try:
        data = load_data_securely()
        
        if data and isinstance(data, dict) and "user_agent" in data:
            logger.info("Successfully loaded user agent from secure storage")
            return data["user_agent"]
        
        logger.info("No user agent found, using default")
        return DEFAULT_USER_AGENT
    except Exception as e:
        logger.error(f"Error loading user agent: {str(e)}")
        return DEFAULT_USER_AGENT