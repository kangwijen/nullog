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
from utils import save_data_to_pickle
from constants import (
    LOGIN_URL, XPATH_MS_LOGIN_BTN, XPATH_EMAIL_INPUT, XPATH_NEXT_BUTTON,
    XPATH_PASSWORD_INPUT, XPATH_SIGN_IN_BUTTON, XPATH_ENRICHMENT_DASHBOARD,
    XPATH_INTERNSHIP_SECTION, XPATH_LOGBOOK_NAV
)
from display import print_info, print_error, print_success, print_warning

def setup_driver():
    try:
        driver_path = ChromeDriverManager().install()
        options = uc.ChromeOptions()
        # options.add_argument('--headless')
        driver = uc.Chrome(driver_executable_path=driver_path, options=options)
        return driver
    except WebDriverException as e:
        print_error(f"Failed to setup Chrome driver: {str(e)}")
        print_error("Please make sure Chrome is installed and updated")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error setting up driver: {str(e)}")
        sys.exit(1)

def navigate_to_page(driver, url, message="Navigating to page..."):
    print_info(message)
    driver.get(url)
    
def wait_for_element(driver, xpath, timeout=10, clickable=False):
    wait = WebDriverWait(driver, timeout)
    if clickable:
        return wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
    else:
        return wait.until(EC.presence_of_element_located((By.XPATH, xpath)))

def login(username=None, password=None):
    driver = None
    try:
        driver = setup_driver()
        
        navigate_to_page(driver, LOGIN_URL, "Navigating to login page...")
        
        try:
            user_agent = driver.execute_script("return navigator.userAgent;")
            print_info(f"Detected User-Agent: {user_agent}")
        except Exception:
            user_agent = None
            print_warning("Could not detect User-Agent, using default")
        
        print_info("Clicking Microsoft login button...")
        try:
            microsoft_login = wait_for_element(driver, XPATH_MS_LOGIN_BTN, timeout=15)
            microsoft_login.click()
        except TimeoutException:
            print_error("Microsoft login button not found. Check if the login page has changed.")
            return None
        
        if not username:
            username = input("Enter your Microsoft email: ")
        if not password:
            password = getpass.getpass("Enter your password: ")
        
        print_info("Entering email...")
        try:
            email_input = wait_for_element(driver, XPATH_EMAIL_INPUT, timeout=15)
            email_input.send_keys(username)
            
            next_button = driver.find_element(By.XPATH, XPATH_NEXT_BUTTON)
            next_button.click()
        except TimeoutException:
            print_error("Email input not found. The login page may have changed.")
            return None
        except Exception as e:
            print_error(f"Error entering email: {str(e)}")
            return None
        
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
        except TimeoutException:
            print_error("Password input or sign-in button not found. The login page may have changed.")
            return None
        except Exception as e:
            print_error(f"Error during sign in: {str(e)}")
            return None
        
        print_info("Handling 'Stay signed in' prompt...")
        try:
            verify = wait_for_element(driver, XPATH_SIGN_IN_BUTTON, clickable=True)
            verify.click()
        except TimeoutException:
            print_info("No 'Stay signed in' prompt detected.")
        
        print_info("Navigating to Enrichment Dashboard...")
        try:
            enrichment = wait_for_element(driver, XPATH_ENRICHMENT_DASHBOARD, timeout=20)
            enrichment.click()
        except TimeoutException:
            print_warning("Enrichment dashboard navigation element not found. May already be on the right page.")
        
        print_info("Navigating to Internship section...")
        try:
            login_internship = wait_for_element(driver, XPATH_INTERNSHIP_SECTION)
            login_internship.click()
        except TimeoutException:
            print_warning("Internship section not found. May already be on the right page.")
        
        print_info("Navigating to Logbook...")
        try:
            time.sleep(2)
            logbook = wait_for_element(driver, XPATH_LOGBOOK_NAV)
            logbook.click()
            time.sleep(2)
        except TimeoutException:
            print_warning("Logbook navigation element not found.")
        
        time.sleep(5)  # Wait for page to fully load
        
        current_url = driver.current_url
        if "login" in current_url.lower() or "auth" in current_url.lower():
            print_error("Login seems to have failed. Still on login/auth page.")
            return None
        
        print_success("Successfully navigated to the logbook!")
        
        cookies = driver.get_cookies()
        if not cookies:
            print_error("No cookies found after login. Authentication may have failed.")
            return None
            
        save_data_to_pickle({"cookies": cookies, "user_agent": user_agent})
        
        return cookies
        
    except WebDriverException as e:
        print_error(f"WebDriver error during login: {str(e)}")
        return None
    except Exception as e:
        print_error(f"An error occurred during login: {str(e)}")
        return None
    finally:
        if driver:
            try:
                time.sleep(3)
                driver.quit()
            except:
                pass
