from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.service import Service
import pickle
import os
import time
import getpass
from webdriver_manager.chrome import ChromeDriverManager

def login(username=None, password=None):
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    
    try:
        print("Navigating to login page...")
        driver.get("https://enrichment.apps.binus.ac.id/Login/Student/Login")
        
        print("Clicking Microsoft login button...")
        microsoft_login = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="btnLogin"]'))
        )
        microsoft_login.click()
        
        if not username:
            username = input("Enter your Microsoft email: ")
        if not password:
            password = getpass.getpass("Enter your password: ")
        
        print("Entering email...")
        email_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="i0116"]'))
        )
        email_input.send_keys(username)
        
        next_button = driver.find_element(By.XPATH, '//*[@id="idSIButton9"]')
        next_button.click()
        
        print("Entering password...")
        password_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="i0118"]'))
        )
        password_input.send_keys(password)
        time.sleep(2)
        
        print("Clicking sign in...")
        signin = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="idSIButton9"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", signin)
        time.sleep(1)
        signin.click()
        
        print("Handling 'Stay signed in' prompt...")
        try:
            verify = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="idSIButton9"]'))
            )
            verify.click()
        except TimeoutException:
            print("No 'Stay signed in' prompt detected.")
        
        print("Navigating to Enrichment Dashboard...")
        try:
            enrichment = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="StudentTermDashboard"]/span[1]/a[2]'))
            )
            enrichment.click()
        except TimeoutException:
            print("Enrichment dashboard navigation element not found. May already be on the right page.")
        
        print("Navigating to Internship section...")
        try:
            login_internship = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="tilesHolder"]/div[1]/div/div[1]/div/div[2]/div[1]'))
            )
            login_internship.click()
        except TimeoutException:
            print("Internship section not found. May already be on the right page.")
        
        print("Navigating to Logbook...")
        try:
            time.sleep(2)
            logbook = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="main-content"]/div[1]/div/div/ul/li[2]'))
            )
            logbook.click()
            time.sleep(2)
        except TimeoutException:
            print("Logbook navigation element not found.")
        
        print("Successfully navigated to the logbook!")
        
        cookies = driver.get_cookies()
        
        cookies_dir = os.path.join(os.path.dirname(__file__), "cookies")
        os.makedirs(cookies_dir, exist_ok=True)
        cookies_file = os.path.join(cookies_dir, "binus_cookies.pkl")
        
        with open(cookies_file, "wb") as f:
            pickle.dump(cookies, f)
        
        print(f"Cookies saved to {cookies_file}")
        
        return cookies
        
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        time.sleep(3)
        driver.quit()
