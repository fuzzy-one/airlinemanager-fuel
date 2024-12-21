import os
import re
import time
from dotenv import load_dotenv
import requests
from datetime import datetime

# Load credentials from .env file
load_dotenv()
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")

# URLs
LOGIN_URL = "https://www.airlinemanager.com/weblogin/login.php"
FUEL_URL = "https://www.airlinemanager.com/fuel.php"
CO2_URL = "https://www.airlinemanager.com/co2.php"
SEND_MSG_URL = "https://www.airlinemanager.com/alliance_chat.php?mode=do"

# Threshold values
FUEL_PRICE_THRESHOLD = 500  # Example threshold for fuel price
CO2_PRICE_THRESHOLD = 120  # Example threshold for CO2 price

# Session setup
session = requests.Session()

# Headers for login
login_headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

# Login payload
login_payload = {
    "lEmail": EMAIL,
    "lPass": PASSWORD,
    "fbSig": "null",
}

# Perform login
login_response = session.post(LOGIN_URL, headers=login_headers, data=login_payload)

if login_response.status_code == 200 and "PHPSESSID" in session.cookies:
    print("Login successful!")
else:
    print("Login failed!")
    print("Response status code:", login_response.status_code)
    print("Response content:", login_response.text)
    exit()


def fetch_page(url, description):
    """Fetch a page and handle errors."""
    try:
        response = session.get(url, headers={"User-Agent": login_headers["User-Agent"]})
        if response.status_code == 200:
            print(f"Successfully fetched {description} page!")
            return response.text
        else:
            print(f"Failed to fetch {description} page!")
            print("Status Code:", response.status_code)
            print("Redirect URL:", response.url)
            return None
    except Exception as e:
        print(f"Error fetching {description} page: {e}")
        return None


def fetch_fuel_timer_and_prices():
    """Fetch the fuel market timer and prices."""
    content = fetch_page(FUEL_URL, "fuel market")
    if content is None:
        return None

    timer_match = re.search(r"fuelTimer'\)\.countdown\(\{\s*until:\s*(\d+),", content)
    prices_match = re.search(r"fuel_startFuelChart\(\[(.*?)\],", content)

    if timer_match and prices_match:
        timer = int(timer_match.group(1))
        prices = prices_match.group(1).split(",")
        return timer, prices
    else:
        print("Could not find fuel market data.")
        return None


def fetch_co2_prices():
    """Fetch the CO2 market prices."""
    content = fetch_page(CO2_URL, "CO2 market")
    if content is None:
        return None

    prices_match = re.search(r"co2_startCo2Chart\(\[(.*?)\],", content)

    if prices_match:
        prices = prices_match.group(1).split(",")
        return prices
    else:
        print("Could not find CO2 market data.")
        return None


def send_message(message):
    """Send a message via a POST request using the existing session."""
    
    utc_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    message_with_time = f"{message} - @ {utc_time}"
    
    # message_payload = {
    #     'alMsg': message,
    #     'fbSig': 'false'
    # }

    message_payload = {
        'alMsg': message_with_time,
        'fbSig': 'false'
    }

    # Define additional headers, if necessary
    send_msg_headers = {
        'User-Agent': "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9,ro;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.airlinemanager.com',
        'Referer': 'https://www.airlinemanager.com/?gameType=web',
        'X-Requested-With': 'XMLHttpRequest',
    }

    # Send the message using session with the additional headers
    response = session.post(SEND_MSG_URL, data=message_payload, headers=send_msg_headers)

    if response.status_code == 200:
        print("Message sent successfully!")
    else:
        print("Failed to send message.")
        print("Status Code:", response.status_code)
        print("Response content:", response.text)



while True:
    # Fetch Fuel Data
    fuel_data = fetch_fuel_timer_and_prices()
    if fuel_data:
        fuel_timer, fuel_prices = fuel_data
        print("Fuel Timer (seconds):", fuel_timer)
        print("Fuel Prices:", fuel_prices)
        print("Last Fuel Price:", fuel_prices[-1])
        
        # Check if fuel price is below threshold
        if float(fuel_prices[-1]) < FUEL_PRICE_THRESHOLD:
            send_message(f"[ fuel-bot ] Fuel price is below {FUEL_PRICE_THRESHOLD}. Last price: {fuel_prices[-1]}.")

    # Fetch CO2 Data
    co2_prices = fetch_co2_prices()
    if co2_prices:
        print("CO2 Prices:", co2_prices)
        print("Last CO2 Price:", co2_prices[-1])

        # Check if CO2 price is below threshold
        if float(co2_prices[-1]) < CO2_PRICE_THRESHOLD:
            send_message(f"[ fuel-bot ] CO2 price is below {CO2_PRICE_THRESHOLD}. Last price: {co2_prices[-1]}.")

    # Sleep until the next refresh
    sleep_time = fuel_timer + 5 if fuel_data else 60
    print(f"Sleeping for {sleep_time} seconds until the next refresh...")
    time.sleep(sleep_time)
