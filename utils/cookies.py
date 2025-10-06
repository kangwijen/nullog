from utils.utils import load_data_securely, logger
from utils.constants import DEFAULT_USER_AGENT
from datetime import datetime, timezone, timedelta

def load_cookies(max_age_minutes=15):
    try:
        data = load_data_securely()
        
        if data:
            if isinstance(data, dict) and "cookies" in data:
                # Freshness guard: ensure cookies are recent
                generated_at_str = data.get("generated_at")
                if generated_at_str:
                    try:
                        generated_at = datetime.fromisoformat(generated_at_str)
                        # Normalize to aware UTC if saved as naive UTC
                        if generated_at.tzinfo is None:
                            generated_at = generated_at.replace(tzinfo=timezone.utc)
                        age = datetime.now(timezone.utc) - generated_at
                        if age <= timedelta(minutes=max_age_minutes):
                            logger.info("Loaded fresh cookies from secure storage")
                            return data["cookies"]
                        else:
                            logger.warning("Stored cookies are stale; forcing fresh login")
                            return None
                    except Exception:
                        logger.warning("Invalid generated_at timestamp; treating cookies as stale")
                        return None
                else:
                    logger.warning("No generated_at timestamp found; treating cookies as stale")
                    return None
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