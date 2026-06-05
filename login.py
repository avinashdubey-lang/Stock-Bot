from SmartApi import SmartConnect
import pyotp

def login_user():

    api_key = "K9Fhvfho"
    username = "AAAN998226"
    password = "3027"

    totp_secret = "UA3PJRBKTOTUQSVH67Y4F5ZEZM"

    totp = pyotp.TOTP(totp_secret).now()

    smartApi = SmartConnect(api_key=api_key)

    session = smartApi.generateSession(
        username,
        password,
        totp
    )

    if not session["status"]:
        raise Exception(session)

    data = session["data"]

    feed_token = data["feedToken"]
    client_code = data["clientcode"]
    jwt_token = data["jwtToken"]

    return smartApi, feed_token, client_code, api_key