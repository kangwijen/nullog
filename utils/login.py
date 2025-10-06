from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.service import Service
import undetected_chromedriver as uc
import time
import getpass
import sys
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime, timezone
from utils.utils import save_data_securely, logger
from utils.constants import (
    LOGIN_URL, XPATH_MS_LOGIN_BTN, XPATH_EMAIL_INPUT, XPATH_NEXT_BUTTON,
    XPATH_PASSWORD_INPUT, XPATH_SIGN_IN_BUTTON, XPATH_ENRICHMENT_DASHBOARD,
    XPATH_INTERNSHIP_SECTION, XPATH_LOGBOOK_NAV, XPATH_ODD_SEMESTER_DROPDOWN,
    XPATH_ODD_SEMESTER_ITEM
)
from utils.display import print_info, print_error, print_success, print_warning

def setup_driver():
    try:
        logger.info("Setting up Chrome driver")
        driver_path = ChromeDriverManager().install()
        options = uc.ChromeOptions()
        # options.add_argument('--headless')
        driver = uc.Chrome(driver_executable_path=driver_path, options=options)
        logger.info("Chrome driver setup successful")
        return driver
    except WebDriverException as e:
        error_msg = f"Failed to setup Chrome driver: {str(e)}"
        logger.error(error_msg)
        print_error(error_msg)
        print_error("Please make sure Chrome is installed and updated")
        sys.exit(1)
    except Exception as e:
        error_msg = f"Unexpected error setting up driver: {str(e)}"
        logger.error(error_msg)
        print_error(error_msg)
        sys.exit(1)

def navigate_to_page(driver, url, message="Navigating to page..."):
    try:
        logger.info(f"Navigating to: {url}")
        print_info(message)
        driver.get(url)
        logger.info("Page navigation successful")
    except Exception as e:
        error_msg = f"Failed to navigate to {url}: {str(e)}"
        logger.error(error_msg)
        print_error(error_msg)
        raise

def wait_for_element(driver, xpath, timeout=10, clickable=False):
    try:
        wait = WebDriverWait(driver, timeout)
        if clickable:
            element = wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        else:
            element = wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        logger.debug(f"Element found: {xpath}")
        return element
    except TimeoutException:
        error_msg = f"Element not found within {timeout} seconds: {xpath}"
        logger.error(error_msg)
        raise TimeoutException(error_msg)
    except Exception as e:
        error_msg = f"Error waiting for element {xpath}: {str(e)}"
        logger.error(error_msg)
        raise

def login(username=None, password=None, is_odd_semester=None):
    driver = None
    try:
        logger.info("Starting login process")
        driver = setup_driver()
        
        navigate_to_page(driver, LOGIN_URL, "Navigating to login page...")
        
        try:
            user_agent = driver.execute_script("return navigator.userAgent;")
            logger.info(f"Detected User-Agent: {user_agent}")
            print_info(f"Detected User-Agent: {user_agent}")
        except Exception as e:
            logger.warning(f"Could not detect User-Agent: {str(e)}")
            user_agent = None
            print_warning("Could not detect User-Agent, using default")
        
        # Click Microsoft login button
        logger.info("Attempting to click Microsoft login button")
        print_info("Clicking Microsoft login button...")
        try:
            microsoft_login = wait_for_element(driver, XPATH_MS_LOGIN_BTN, timeout=15)
            microsoft_login.click()
            logger.info("Microsoft login button clicked successfully")
        except TimeoutException:
            error_msg = "Microsoft login button not found. Check if the login page has changed."
            logger.error(error_msg)
            print_error(error_msg)
            return None
        
        # Get credentials
        if not username:
            username = input("Enter your Microsoft email: ")
        if not password:
            password = getpass.getpass("Enter your password: ")
        
        if not username or not password:
            error_msg = "Username and password are required"
            logger.error(error_msg)
            print_error(error_msg)
            return None
        
        # Enter email
        logger.info("Entering email address")
        print_info("Entering email...")
        try:
            email_input = wait_for_element(driver, XPATH_EMAIL_INPUT, timeout=15)
            email_input.send_keys(username)
            
            next_button = driver.find_element(By.XPATH, XPATH_NEXT_BUTTON)
            next_button.click()
            logger.info("Email entered and next button clicked")
        except TimeoutException:
            error_msg = "Email input not found. The login page may have changed."
            logger.error(error_msg)
            print_error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Error entering email: {str(e)}"
            logger.error(error_msg)
            print_error(error_msg)
            return None
        
        # Enter password
        logger.info("Entering password")
        print_info("Entering password...")
        try:
            password_input = wait_for_element(driver, XPATH_PASSWORD_INPUT, timeout=15)
            password_input.send_keys(password)
            time.sleep(2)
            
            print_info("Clicking sign in...")
            signin = wait_for_element(driver, XPATH_SIGN_IN_BUTTON, clickable=True, timeout=15)
            driver.execute_script("arguments[0].scrollIntoView(true);", signin)
            time.sleep(1)
            signin.click()
            logger.info("Password entered and sign in clicked")
        except TimeoutException:
            error_msg = "Password input or sign-in button not found. The login page may have changed."
            logger.error(error_msg)
            print_error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Error during sign in: {str(e)}"
            logger.error(error_msg)
            print_error(error_msg)
            return None
        
        # Handle "Stay signed in" prompt
        logger.info("Handling 'Stay signed in' prompt")
        print_info("Handling 'Stay signed in' prompt...")
        try:
            verify = wait_for_element(driver, XPATH_SIGN_IN_BUTTON, clickable=True)
            verify.click()
            logger.info("'Stay signed in' prompt handled")
        except TimeoutException:
            logger.info("No 'Stay signed in' prompt detected")
            print_info("No 'Stay signed in' prompt detected.")
        
        # Optional: select odd semester if requested by caller (before navigating to Enrichment Dashboard)
        if is_odd_semester is True:
            logger.info("Odd semester flag set. Selecting odd semester from dropdown")
            print_info("Selecting odd semester...")
            try:
                dropdown = wait_for_element(driver, XPATH_ODD_SEMESTER_DROPDOWN, clickable=True, timeout=15)
                driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
                time.sleep(1)
                dropdown.click()
                item = wait_for_element(driver, XPATH_ODD_SEMESTER_ITEM, clickable=True, timeout=15)
                item.click()
                logger.info("Odd semester selected. Waiting 7 seconds for page to update")
                time.sleep(7)
            except TimeoutException:
                logger.warning("Odd semester dropdown or item not found")
                print_warning("Odd semester selection controls not found.")
            except Exception as e:
                logger.warning(f"Error selecting odd semester: {str(e)}")
                print_warning(f"Error selecting odd semester: {str(e)}")

        # Navigate to Enrichment Dashboard
        logger.info("Navigating to Enrichment Dashboard")
        print_info("Navigating to Enrichment Dashboard...")
        try:
            enrichment = wait_for_element(driver, XPATH_ENRICHMENT_DASHBOARD, timeout=20)
            enrichment.click()
            logger.info("Enrichment dashboard navigation successful")
        except TimeoutException:
            logger.warning("Enrichment dashboard navigation element not found")
            print_warning("Enrichment dashboard navigation element not found. May already be on the right page.")
        
        # Navigate to Internship section
        logger.info("Navigating to Internship section")
        print_info("Navigating to Internship section...")
        try:
            login_internship = wait_for_element(driver, XPATH_INTERNSHIP_SECTION)
            login_internship.click()
            logger.info("Internship section navigation successful")
        except TimeoutException:
            logger.warning("Internship section not found")
            print_warning("Internship section not found. May already be on the right page.")
        
        # Navigate to Logbook
        logger.info("Navigating to Logbook")
        print_info("Navigating to Logbook...")
        try:
            time.sleep(2)
            logbook = wait_for_element(driver, XPATH_LOGBOOK_NAV)
            logbook.click()
            time.sleep(2)
            logger.info("Logbook navigation successful")
        except TimeoutException:
            logger.warning("Logbook navigation element not found")
            print_warning("Logbook navigation element not found.")
        
        time.sleep(5)  # Wait for page to fully load
        
        # Verify successful login
        current_url = driver.current_url
        if "login" in current_url.lower() or "auth" in current_url.lower():
            error_msg = "Login seems to have failed. Still on login/auth page."
            logger.error(error_msg)
            print_error(error_msg)
            return None
        
        logger.info("Successfully navigated to the logbook")
        print_success("Successfully navigated to the logbook!")
        
        # Get and save cookies
        cookies = driver.get_cookies()
        if not cookies:
            error_msg = "No cookies found after login. Authentication may have failed."
            logger.error(error_msg)
            print_error(error_msg)
            return None
        
        logger.info(f"Retrieved {len(cookies)} cookies")
        
        # Save data securely with freshness timestamp
        data_to_save = {
            "cookies": cookies,
            "user_agent": user_agent,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }
        if save_data_securely(data_to_save):
            logger.info("Login data saved securely")
            return cookies
        else:
            logger.error("Failed to save login data")
            return None
        
    except WebDriverException as e:
        error_msg = f"WebDriver error during login: {str(e)}"
        logger.error(error_msg)
        print_error(error_msg)
        return None
    except Exception as e:
        error_msg = f"An error occurred during login: {str(e)}"
        logger.error(error_msg)
        print_error(error_msg)
        return None
    finally:
        if driver:
            try:
                logger.info("Closing browser")
                time.sleep(3)
                driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")
                pass
