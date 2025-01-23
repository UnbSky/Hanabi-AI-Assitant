import sys
import json
def printf(*args):
    print(*args, flush=True)

# Imports (3rd-party)
import requests
from PyQt5 import QtWidgets, QtCore

# Imports (local application)
from game_ui import AIWindow
from play_util import load_model

# Authenticate, login to the WebSocket server, and run forever.
def login_to_hanab(username, password):
    if username == "":
        printf('error: "HANABI_USERNAME" is blank in the ".env" file')
        sys.exit(1)
    if password == "":
        printf('error: "HANABI_PASSWORD" is blank in the ".env" file')
        sys.exit(1)

    # The official site uses HTTPS.
    protocol = "https"
    ws_protocol = "wss"
    host = "hanab.live"
    path = "/login"
    ws_path = "/ws"
    url = protocol + "://" + host + path
    ws_url = ws_protocol + "://" + host + ws_path
    printf('Authenticating to "' + url + '" with a username of "' + username + '".')
    resp = requests.post(
        url,
        {
            "username": username,
            "password": password,
            # This is normally supposed to be the version of the JavaScript
            # client, but the server will also accept "bot" as a valid version.
            "version": "bot",
        },
    )

    # Handle failed authentication and other errors.
    if resp.status_code != 200:
        printf("Authentication failed:")
        printf(resp.text)
        sys.exit(1)

    # Scrape the cookie from the response.
    cookie = ""
    for header in resp.headers.items():
        if header[0] == "Set-Cookie":
            cookie = header[1]
            break
    if cookie == "":
        printf("Failed to parse the cookie from the authentication response headers:")
        printf(resp.headers)
        sys.exit(1)

    return ws_url, cookie

def main():
    with open(f'user_config.json', 'r') as json_file:
        user_args = json.load(json_file)
    username = user_args["username"]
    password = user_args["password"]
    model_name = user_args["model"]
    online = user_args["online"]

    printf("Load Model")
    model, action_dict_toact, action_dict_toid, output_action_dict_toact, output_action_dict_toid, device = load_model(model_name)

    ws_url = None
    cookie = None
    if online:
        printf("Try Login")
        ws_url, cookie = login_to_hanab(username, password)

    printf("Launch UI")
    #QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling)
    app = QtWidgets.QApplication(sys.argv)
    MyUiStart = AIWindow(ws_url, cookie, [model, action_dict_toact, action_dict_toid, output_action_dict_toact, output_action_dict_toid, device])
    MyUiStart.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

#UnbSky_bot
#unbbot

#迭代式的
