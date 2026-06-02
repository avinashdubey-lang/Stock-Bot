from SmartApi import SmartConnect
import pyotp

api_key = "K9Fhvfho"
client_id = "AAAN998226"
password = "3027"
totp_secret = "UA3PJRBKTOTUQSVH67Y4F5ZEZM"

smartApi = SmartConnect(api_key)

totp = pyotp.TOTP(totp_secret).now()

data = smartApi.generateSession(
    client_id,
    password,
    totp
)

print(data)