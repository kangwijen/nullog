COOKIES_DIR = "cookies"
COOKIES_FILE = "cookies.pkl"

BASE_URL = "https://activity-enrichment.apps.binus.ac.id"
LOGIN_URL = "https://enrichment.apps.binus.ac.id/Login/Student/Login"
LOGBOOK_GET_MONTHS_URL = f"{BASE_URL}/LogBook/GetMonths"
LOGBOOK_GET_LOGBOOK_URL = f"{BASE_URL}/LogBook/GetLogBook"
LOGBOOK_STUDENT_SAVE_URL = f"{BASE_URL}/LogBook/StudentSave"
REFERER_URL = f"{BASE_URL}/LearningPlan/StudentIndex"

XPATH_MS_LOGIN_BTN = '//*[@id="btnLogin"]'
XPATH_EMAIL_INPUT = '//*[@id="i0116"]'
XPATH_NEXT_BUTTON = '//*[@id="idSIButton9"]'
XPATH_PASSWORD_INPUT = '//*[@id="i0118"]'
XPATH_SIGN_IN_BUTTON = '//*[@id="idSIButton9"]'
XPATH_ENRICHMENT_DASHBOARD = '//*[@id="StudentTermDashboard"]/span[1]/a[2]'
XPATH_INTERNSHIP_SECTION = '//*[@id="tilesHolder"]/div[1]/div/div[1]/div/div[2]/div[1]'
XPATH_LOGBOOK_NAV = '//*[@id="main-content"]/div[1]/div/div/ul/li[2]'

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'

WEEKDAY_SATURDAY = 5
WEEKDAY_SUNDAY = 6
