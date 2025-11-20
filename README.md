# 🎵 Spotify LLM Organizer

**Organize your music with AI.**

This application uses Google's Gemini 3 Pro model to intelligently classify your Spotify library (Liked Songs or specific playlists) into mood and genre-based playlists. It features a robust caching system, a manual review process, and a batch processing workflow designed to handle large libraries efficiently.

## ✨ Features

*   **AI-Powered Classification**: Uses Gemini 3 Pro to analyze artist, title, and metadata to determine the best category.
*   **Smart Categories**: Pre-defined categories including "Punjabi - Hype", "Hindi - Bollywood", "English - Pop", "Gym - Phonk", "Sad/Emotional", and more.
*   **Web GUI**: Clean, minimal Streamlit interface with progress tracking and visual controls.
*   **3-Step Workflow**: Fetch, Classify, and Apply steps are separated to give you control.
*   **Caching System**: Caches track metadata and classification results locally to minimize API usage and speed up subsequent runs.
*   **Edit Classifications**: Review and modify classifications directly in the GUI before applying.
*   **Progress Persistence**: App remembers your progress across sessions.
*   **Batch Processing**: Processes songs in parallel batches for speed.

## 🚀 Getting Started

### Prerequisites

1.  **Python 3.8+**
2.  **Spotify Developer Account**: Create an app at [developer.spotify.com](https://developer.spotify.com/dashboard) to get a Client ID and Secret.
3.  **Google AI Studio Key**: Get an API key for Gemini at [aistudio.google.com](https://aistudio.google.com/).

### Installation

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd spotify_organiser
    ```

2.  Create a virtual environment and install dependencies:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  Create a `.env` file in the root directory:
    ```env
    SPOTIFY_CLIENT_ID=your_spotify_client_id
    SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
    SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
    
    GOOGLE_API_KEY=your_gemini_api_key
    GEMINI_MODEL=gemini-3.0-pro-exp
    
    # Optional
    BATCH_SIZE=100
    CONFIDENCE_THRESHOLD=0.8
    USE_MOCKS=False
    ```

## 📖 Usage

### Web GUI (Recommended)
Launch the Streamlit web interface:
```bash
streamlit run app.py
```

The GUI provides:
*   **Step 1: Fetch** - Download tracks from Spotify (Liked Songs or Playlist)
*   **Step 2: Classify** - AI classification with real-time progress
*   **Step 3: Apply** - Create/update playlists in your Spotify account

**Features:**
*   Progress tracking across sessions
*   Edit classifications with dropdowns
*   Visual confidence scores
*   Category breakdowns
*   One-click approval

### CLI (Alternative)

The app also supports a command-line workflow:

#### Step 1: Fetch Tracks
```bash
# Fetch Liked Songs
python main.py --fetch

# Fetch a specific playlist
python main.py --fetch --source playlist --playlist-id <playlist_id>
```

#### Step 2: Classify
```bash
python main.py --classify
```

#### Step 3: Apply
```bash
python main.py --apply
```

## 🧠 Data Flow

1.  **Spotify API** ➡️ `SpotifyClient` fetches track metadata.
2.  **Cache** ➡️ Data is stored in `.cache/tracks_metadata.json`.
3.  **LLM Classifier** ➡️ Reads tracks, sends batches to **Gemini API**.
4.  **Review** ➡️ Classifications are saved to `.review/classification_review.json`.
5.  **User Action** ➡️ User approves the review file.
6.  **Playlist Manager** ➡️ Reads review file, calls **Spotify API** to create playlists.

## 📂 Project Structure

*   `main.py`: CLI entry point and workflow orchestrator.
*   `llm_classifier.py`: Handles interaction with Google's Gemini API.
*   `spotify_client.py`: Wrapper for Spotify API (Spotipy) with mock support.
*   `playlist_manager.py`: Logic for creating and updating playlists.
*   `cache_manager.py`: Manages local JSON caching of tracks and results.
*   `review_manager.py`: Handles the generation and validation of the review file.
*   `config.py`: Central configuration and category definitions.

## 🛠️ Troubleshooting

*   **403 Forbidden (Spotify)**: Ensure your Spotify App is in "Development Mode" and you have added your email to the "Users" list in the Spotify Dashboard.
*   **Rate Limits**: The app has built-in delays, but if you hit limits, wait a few minutes.
*   **Gemini Errors**: Ensure your API key is valid and has access to the `gemini-3.0-pro-exp` model.

## 🛡️ Privacy

This tool runs locally. Your Spotify data is only sent to Google's API for classification purposes and is not stored on any third-party servers by this application.
