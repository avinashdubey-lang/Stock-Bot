def login_user():
    try:
        from SmartApi import SmartConnect
        import pyotp

        API_KEY = "K9Fhvfho"
        CLIENT_ID = "AAAN998226"
        PASSWORD = "3027"
        TOTP_SECRET = "UA3PJRBKTOTUQSVH67Y4F5ZEZM"

        smartApi = SmartConnect(API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()

        session = smartApi.generateSession(
            CLIENT_ID,
            PASSWORD,
            totp
        )

        if not session["status"]:
            raise Exception(f"Login Failed: {session}")

        print("Login Successful")
        return smartApi, session

    except Exception as e:
        print("LOGIN ERROR:", e)
        raise