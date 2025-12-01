import requests
from dotenv import load_dotenv
import os
load_dotenv()

import spotipy
from spotipy.oauth2 import SpotifyOAuth


CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

sp_oauth = SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope="user-read-private"
)

def get_auth_url():
    auth_url = sp_oauth.get_authorize_url()
    return auth_url

def get_token(code: str):
    token_info = sp_oauth.get_access_token(code)
    return token_info

def get_user_profile(token: str):
    headers = {
        "Authorization": f"Bearer {token}"
    }
    response = requests.get("https://api.spotify.com/v1/me", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        return None
    
def get_top_tracks(token: str):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get("https://api.spotify.com/v1/me/top/tracks", headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error Spotify:", response.status_code, response.text)
        return None

def refresh_token(refresh_token: str):
    new_token_info = sp_oauth.refresh_access_token(refresh_token)
    return new_token_info

