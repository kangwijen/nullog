import os
import pickle

def load_cookies():
    cookies_file = os.path.join(os.path.dirname(__file__), "cookies", "binus_cookies.pkl")
    
    if os.path.exists(cookies_file):
        with open(cookies_file, "rb") as f:
            return pickle.load(f)
    else:
        print("No saved cookies found.")
        return None