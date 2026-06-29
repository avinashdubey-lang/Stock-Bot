#login.py
from SmartApi import SmartConnect
import pyotp
import time


def login_user(account):

    api_key = account["api_key"]
    username = account["client_code"]
    password = account["password"]
    totp_secret = account["totp_secret"]

    totp = pyotp.TOTP(totp_secret).now()

    smartApi = SmartConnect(api_key=api_key)

    for attempt in range(3):

        try:

            session = smartApi.generateSession(
                username,
                password,
                totp
            )

            break

        except Exception as e:

            print(f"⚠️ Login attempt {attempt + 1} failed for {account['name']}")
            print(e)

            if attempt == 2:
                raise

            print("⏳ Retrying in 5 seconds...")
            time.sleep(5)

    if not session["status"]:
        raise Exception(session)

    data = session["data"]

    return (
        smartApi,
        data["feedToken"],
        data["clientcode"],
        api_key,
        data["jwtToken"]
    )