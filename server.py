from flask import Flask, request, jsonify
from flask_cors import CORS
from ytmusicapi import YTMusic
import requests
import re
import logging

app = Flask(__name__)
CORS(app)
ytmusic = YTMusic()

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
KOBOLD_API_URL = "http://127.0.0.1:5001/api/v1/generate"

# System prompts
CHAT_SYSTEM_PROMPT = """You are an AI assistant that helps with music queries and chat.
You have access to a music player and can play songs by suggesting them.
When a user asks to play a song, respond with the song and artist information,
and also include a special command in this format: [PLAY]: <song name> by <artist>.
"""

PLAY_AI_SYSTEM_PROMPT = """You are an AI assistant that helps with music queries.
Based on the conversation history, suggest a song that the user might enjoy.
"""


def generate_ai_response(prompt, max_length=80):
    """Generate a response from the AI model."""
    payload = {
        "max_context_length": 2048,
        "max_length": max_length,
        "prompt": prompt,
        "quiet": False,
        "rep_pen": 1.02,
        "rep_pen_range": 256,
        "rep_pen_slope": 1,
        "temperature": 0.5,
        "top_p": 0.9,
        "typical": 1,
        "stop_sequence": ["<|user|>", "Human:"]
    }

    try:
        response = requests.post(KOBOLD_API_URL, json=payload)
        result = response.json()

        if "results" in result and isinstance(result["results"], list) and len(result["results"]) > 0:
            return result["results"][0].get("text", "")
        else:
            return result.get("text", "")
    except Exception as e:
        logger.error(f"Error calling AI API: {str(e)}")
        return ""


@app.route('/search', methods=['POST'])
def search():
    """Search for a song on YouTube Music and return the playable URL."""
    try:
        data = request.get_json()
        if not data or 'song_title' not in data or 'artist_name' not in data:
            return jsonify({"error": "Invalid request"}), 400

        song_title = data['song_title']
        artist_name = data['artist_name']
        search_query = f"{song_title} {artist_name}"
        logger.debug(f"Searching for: {search_query}")

        # Search for songs using ytmusicapi
        search_results = ytmusic.search(search_query, filter="songs")
        if not search_results:
            return jsonify({"error": "No results found"}), 404

        # Find the best matching result
        matching_result = None
        for result in search_results:
            artists = result.get('artists') or []
            for a in artists:
                if artist_name.lower() in a.get('name', '').lower():
                    matching_result = result
                    break
            if matching_result:
                break

        # If no match found, use the first result
        if not matching_result:
            matching_result = search_results[0]

        video_id = matching_result.get('videoId')
        if not video_id:
            return jsonify({"error": "Video ID not found in search result"}), 404

        video_url = f"https://music.youtube.com/watch?v={video_id}"
        return jsonify({
            "url": video_url,
            "title": matching_result.get('title', song_title),
            "artist": matching_result.get('artists', [{'name': artist_name}])[0].get('name', artist_name)
        })

    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat messages and check for song play requests."""
    try:
        data = request.get_json()
        message = data.get("message")
        if not message:
            return jsonify({"error": "No message provided"}), 400

        # Build prompt for regular chat
        prompt = (
            f"<|system|>{CHAT_SYSTEM_PROMPT}\n"
            f"<|user|>{message}\n"
            "<|assistant|>"
        )

        full_text = generate_ai_response(prompt)
        logger.debug(f"AI response: {full_text}")

        # Check if there's a play command in the response
        play_match = re.search(r"\[PLAY\]:\s*(.*?)\s+by\s+(.*?)(?:\.|$|\n)", full_text, re.IGNORECASE)

        if play_match:
            song = play_match.group(1).strip()
            artist = play_match.group(2).strip()

            # Remove the play command from the display text
            display_text = re.sub(r"\[PLAY\]:\s*(.*?)\s+by\s+(.*?)(?:\.|$|\n)", "", full_text).strip()

            return jsonify({
                "reply": display_text or full_text,
                "play_command": {
                    "song": song,
                    "artist": artist
                }
            })

        return jsonify({"reply": full_text})

    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/play_ai', methods=['POST'])
def play_ai():
    """Analyze chat history and suggest a song to play."""
    try:
        data = request.get_json()
        chat_history = data.get("chat_history", "")

        # Build ChatML prompt using the prior conversation
        prompt = (
            f"<|system|>{PLAY_AI_SYSTEM_PROMPT}\n"
            f"<|user|>Here is the conversation history:\n{chat_history}\n"
            "Now, please provide ONLY the song name and artist name in the following format:\n"
            "Song: <song name> by <artist>\n"
            "<|assistant|>"
        )

        full_text = generate_ai_response(prompt)
        logger.debug(f"Play AI response: {full_text}")

        # Parse song and artist using regex
        match = re.search(r"Song:\s*(.*?)\s+by\s+(.*)", full_text, re.IGNORECASE)
        if match:
            song = match.group(1).strip()
            artist = match.group(2).strip()
            return jsonify({
                "song": song,
                "artist": artist
            })
        else:
            return jsonify({"error": "Could not extract song information from AI response"}), 400

    except Exception as e:
        logger.error(f"Play AI error: {str(e)}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)