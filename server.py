from flask import Flask, request, jsonify
from flask_cors import CORS
from ytmusicapi import YTMusic
import requests
import re
import logging

app = Flask(__name__)
CORS(app)
ytmusic = YTMusic()

@app.route('/search', methods=['POST'])
def search():
    try:
        data = request.get_json()
        if not data or 'song_title' not in data or 'artist_name' not in data:
            return jsonify({"error": "Invalid request"}), 400

        song_title = data['song_title']
        artist_name = data['artist_name']
        search_query = f"{song_title} {artist_name}"

        # Search for songs using ytmusicapi
        search_results = ytmusic.search(search_query, filter="songs")
        if not search_results:
            return jsonify({"error": "No results found"}), 404

        matching_result = None
        for result in search_results:
            artists = result.get('artists') or []
            for a in artists:
                if artist_name.lower() in a.get('name', '').lower():
                    matching_result = result
                    break
            if matching_result:
                break

        if not matching_result:
            matching_result = search_results[0]

        video_id = matching_result.get('videoId')
        if not video_id:
            return jsonify({"error": "Video ID not found in search result"}), 404

        video_url = f"https://music.youtube.com/watch?v={video_id}"
        return jsonify({"url": video_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        message = data.get("message")
        if not message:
            return jsonify({"error": "No message provided"}), 400

        # Build prompt for regular chat (using ChatML is optional here)
        prompt = (
            "<|system|>You are an AI assistant that helps with music queries and chat.\n"
            "<|user|> " + message + "\n"
            "<|assistant|>"
        )

        kobold_url = "http://127.0.0.1:5001/api/v1/generate"
        payload = {
            "max_context_length": 2048,
            "max_length": 80,
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
        kobold_response = requests.post(kobold_url, json=payload)
        result = kobold_response.json()

        if "results" in result and isinstance(result["results"], list) and len(result["results"]) > 0:
            full_text = result["results"][0].get("text", "")
        else:
            full_text = result.get("text", "")

        hidden_reply = ""
        for line in full_text.splitlines():
            if line.strip().startswith("[HIDDEN]:"):
                hidden_reply = line.strip()[len("[HIDDEN]:"):].strip()
                break

        app.logger.debug("Full generated text: %s", full_text)
        app.logger.debug("Parsed hidden reply: %s", hidden_reply)

        return jsonify({"reply": full_text, "hidden": hidden_reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/play_ai', methods=['POST'])
def play_ai():
    try:
        data = request.get_json()
        chat_history = data.get("chat_history", "")
        # Build ChatML prompt using the prior conversation.
        # Here we use ChatML tokens for each role.
        prompt = (
            "<|system|>You are an AI assistant that helps with music queries.\n"
            "<|user|> Here is the conversation history:\n" + chat_history + "\n"
            "Now, please provide ONLY the song name and artist name in the following format:\n"
            "Song: <song name> by <artist>\n"
            "<|assistant|>"
        )

        kobold_url = "http://127.0.0.1:5001/api/v1/generate"
        payload = {
            "max_context_length": 2048,
            "max_length": 80,
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
        kobold_response = requests.post(kobold_url, json=payload)
        result = kobold_response.json()

        if "results" in result and isinstance(result["results"], list) and len(result["results"]) > 0:
            full_text = result["results"][0].get("text", "")
        else:
            full_text = result.get("text", "")

        # Use regex to parse expected format: "Song: <song name> by <artist>"
        match = re.search(r"Song:\s*(.*?)\s+by\s+(.*)", full_text, re.IGNORECASE)
        if match:
            song = match.group(1).strip()
            artist = match.group(2).strip()
            song_artist = f"{song}|{artist}"  # using a delimiter for splitting on client side
        else:
            song_artist = ""

        app.logger.debug("Play AI full generated text: %s", full_text)
        app.logger.debug("Extracted song/artist: %s", song_artist)

        return jsonify({"song_artist": song_artist})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True)
