import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import os

def refresh_token():
    sp_oauth = SpotifyOAuth(
        client_id="c86f7613eb3c42318201c2e24625ab71",
        client_secret="84ddcc1d0cd046d4be5122a8f9e453c0", 
        redirect_uri="http://127.0.0.1:8090/callback",
        scope="playlist-modify-public playlist-modify-private user-read-playback-state user-modify-playback-state user-read-currently-playing playlist-read-private user-read-recently-played user-top-read user-library-read",
        cache_path=".cache",
        open_browser=True
    )
    
    # Force refresh by clearing and re-authenticating
    sp = spotipy.Spotify(auth_manager=sp_oauth)
    
    try:
        user = sp.me()
        print(f"✅ Successfully authenticated as: {user['display_name']}")
        
        # Test creating a playlist to make sure permissions work
        test_playlist = sp.user_playlist_create(
            user=user['id'],
            name="Test Playlist - Delete Me",
            public=False,
            description="Test playlist created by Spotify MCP"
        )
        print(f"✅ Test playlist created: {test_playlist['name']}")
        
        # Delete the test playlist
        sp.user_playlist_unfollow(user['id'], test_playlist['id'])
        print("✅ Test playlist deleted")
        
        print("🎉 Authentication successful and token saved!")
        
        # Print token info
        with open('.cache', 'r') as f:
            token_data = json.load(f)
            print(f"📁 Token saved to: {os.path.abspath('.cache')}")
            if 'expires_at' in token_data:
                import time
                remaining = token_data['expires_at'] - time.time()
                print(f"⏰ Token expires in {remaining/3600:.1f} hours")
        
    except Exception as e:
        print(f"❌ Authentication failed: {e}")
        print("Make sure you:")
        print("1. Have spotipy installed: pip install spotipy")
        print("2. Your Spotify app settings allow the redirect URI")
        print("3. You complete the browser authentication flow")

if __name__ == "__main__":
    print("🎵 Refreshing Spotify token...")
    refresh_token()