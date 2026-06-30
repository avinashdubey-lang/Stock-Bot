from SmartApi import SmartConnect
import pyotp
import time
from config import API_KEY, CLIENT_CODE, PASSWORD, TOTP_SECRET


def login_user():

    api_key = API_KEY
    username = CLIENT_CODE
    password = PASSWORD
    totp_secret = TOTP_SECRET

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

            print(f"⚠️ Login attempt {attempt + 1} failed:")
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