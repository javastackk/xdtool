import requests

URL = "https://raw.githubusercontent.com/javastackk/xdtool-host/main/latest.json"

def check_update():
    data = requests.get(URL).json()
    return data["latest"]