# Spotify LLM Organizer

Automatically organize your Spotify liked songs or playlists into categorized playlists. This tool can use a local LLM for classification but also works in a lightweight mock mode without any external dependencies.

## Features

- **Multiple Sources**: Organize your liked songs or any of your playlists.
- **Smart Caching**: Resumes where you left off. Already classified songs are skipped.
- **Mock Mode**: Runs without Spotify credentials or a local LLM for quick demos.
- **Rule-Based Classification**: Uses metadata for quick and accurate categorization of obvious tracks (e.g., "Oldies", "Instrumental").
- **LLM-Powered**: Can connect to a local OpenAI-compatible endpoint (like vLLM) for advanced classification of ambiguous tracks.

## Categories

- **English**: English language songs
- **Hindi**: Hindi language songs
- **Punjabi**: Punjabi language songs
- **Phonk/Instrumental**: Instrumental tracks and phonk music
- **Oldies**: Classic Hindi songs from pre-2000.
- **Misc**: Songs that don't fit other categories.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```
*Note: `requirements.txt` includes `spotipy` and `openai`, but the app will run in mock mode if they are not installed.*

### 2. Configure (Optional: For Real Spotify)

To connect to your real Spotify account, you need credentials.

1.  Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard) and create an app.
2.  Add `http://127.0.0.1:8888/callback` as a "Redirect URI" in the app settings.
3.  Create a `.env` file (you can copy `.env.example`) and add your credentials:
    ```
    SPOTIFY_CLIENT_ID=your_client_id
    SPOTIFY_CLIENT_SECRET=your_client_secret
    ```
4.  To disable mock mode, set `USE_MOCKS=0` in your environment.

### 3. Run the App

The app runs in **mock mode** by default if no `.env` file is found.

**Organize your (mock) liked songs:**
```bash
python3 main.py --source liked
```

**Do a dry run without creating playlists:**
```bash
python3 main.py --source liked --dry-run
```

**Organize a real playlist (requires `.env` file):**
```bash
python3 main.py --source playlist --playlist-id <YOUR_PLAYLIST_ID>
```

**Clear the cache and start fresh:**
```bash
python3 main.py --source liked --clear-cache
```

## How It Works

1.  **Authentication**: Connects to Spotify via OAuth2 if credentials are provided. Falls back to mock data otherwise.
2.  **Fetch & Cache**: Retrieves tracks and immediately saves them to the `.cache` directory.
3.  **Classify**:
    - Checks cache first.
    - Applies simple metadata rules (e.g., artist name, release year).
    - If an LLM endpoint is configured, uses it for ambiguous songs.
    - Falls back to a simple rule-based classifier if no LLM is available.
4.  **Organize**: Creates new private playlists named `autosorted-*` in your Spotify account. Your original playlists are never modified.

## Features

- ✅ **Fast parallel processing** with vLLM (10x faster than sequential)
- ✅ **Persistent caching** - never lose Spotify data or classifications
- ✅ **Resumable** - interrupted? Just restart and continue
- ✅ **Smart rules** - instant detection of classic artists and genres
- ✅ **Confidence scoring** - uncertain tracks go to "Misc"
- ✅ **Privacy-focused** - runs 100% locally, no data leaves your machine
- ✅ **Non-destructive** - original playlists unchanged
- ✅ **Progress tracking** - beautiful CLI with real-time updates

## Troubleshooting

**"Connection refused" error**: 
```bash
# Check if vLLM is running
docker-compose ps
# If not, start it
docker-compose up -d
```

**"Invalid credentials"**: Check your `.env` file has correct Spotify Client ID/Secret

**"Out of memory"**: Reduce batch size in `.env`:
```bash
BATCH_SIZE=10
MAX_WORKERS=5
```

**vLLM won't start (no GPU)**:
Edit `docker-compose.yml` and remove the GPU sections, or use CPU mode:
```yaml
command: >
  --model google/gemma-2-2b-it
  --dtype float32
```

**Classifications seem wrong**: Adjust confidence threshold in `.env`:
```bash
CONFIDENCE_THRESHOLD=0.8  # Higher = more strict (more go to Misc)
```

## Cache Management

The app caches:
- **Spotify track metadata** (`.cache/tracks_metadata.json`)
- **LLM classifications** (`.cache/classifications.json`)
- **Fetch sessions** (`.cache/fetch_sessions.json`)

Benefits:
- No repeated Spotify API calls
- Resume interrupted classifications
- Instant re-runs

To clear cache:
```bash
python3 main.py --source liked --clear-cache
```

## Project Structure

```
spotify_organiser/
├── main.py                 # CLI entry point
├── spotify_client.py       # Spotify API wrapper
├── llm_classifier.py       # vLLM integration
├── classifier.py           # Classification orchestration
├── playlist_manager.py     # Playlist creation
├── cache_manager.py        # Persistent caching
├── config.py               # Configuration
├── docker-compose.yml      # vLLM server setup
├── requirements.txt        # Python dependencies
├── .env.example            # Configuration template
└── tests/                  # Test suite
    ├── test_cache.py
    ├── test_llm_mock.py
    ├── test_classifier_rules.py
    └── run_all_tests.py
```

## License

MIT

