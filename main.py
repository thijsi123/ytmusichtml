from ytmusicapi import YTMusic
import random
import webbrowser

# Initialize YouTube Music API
ytmusic = YTMusic()

# List of song titles
song_titles = ["Never Stop Speedcore - Vieze Asbak"]

# Pick a random song
random_song = random.choice(song_titles)

# Search for the song
search_results = ytmusic.search(random_song)

# Get the first result and its videoId
video_id = search_results[0]['videoId']

# Generate a URL to play the song
url = f"https://music.youtube.com/watch?v={video_id}"

# Open the URL in a web browser
print(f"Playing: {random_song}")
print(f"Opening URL: {url}")
webbrowser.open(url)
