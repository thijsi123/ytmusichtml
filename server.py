from flask import Flask, request, jsonify
from flask_cors import CORS
from ytmusicapi import YTMusic

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

        # Perform a search using ytmusicapi (filtering for songs)
        search_results = ytmusic.search(search_query, filter="songs")
        if not search_results:
            return jsonify({"error": "No results found"}), 404

        # Try to find a result with a matching artist name
        matching_result = None
        for result in search_results:
            # 'artists' is usually a list of dictionaries with a 'name' key
            artists = result.get('artists') or []
            for a in artists:
                if artist_name.lower() in a.get('name', '').lower():
                    matching_result = result
                    break
            if matching_result:
                break

        # Fallback: if no match, pick the first result
        if not matching_result:
            matching_result = search_results[0]

        video_id = matching_result.get('videoId')
        if not video_id:
            return jsonify({"error": "Video ID not found in search result"}), 404

        video_url = f"https://music.youtube.com/watch?v={video_id}"
        return jsonify({"url": video_url})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
