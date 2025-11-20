"""Streamlit GUI for Spotify LLM Organizer."""
import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict

from spotify_client import SpotifyClient
from llm_classifier import LLMClassifier
from playlist_manager import PlaylistManager
from cache_manager import CacheManager
from review_manager import ReviewManager
from config import Config

# Page config
st.set_page_config(
    page_title="Spotify Organizer",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Spotify dark theme
st.markdown("""
<style>
    /* Main app background */
    .main {
        padding: 2rem;
        background-color: #121212;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background-color: #000000;
    }
    
    /* All text to white/light gray */
    .main * {
        color: #FFFFFF !important;
    }
    
    /* Buttons - Spotify green */
    .stButton button {
        width: 100%;
        border-radius: 8px;
        height: 3rem;
        font-weight: 600;
        background-color: #1DB954 !important;
        color: #FFFFFF !important;
        border: none;
    }
    
    .stButton button:hover {
        background-color: #1ed760 !important;
    }
    
    /* Primary buttons */
    .stButton button[kind="primary"] {
        background-color: #1DB954 !important;
    }
    
    /* Input fields */
    .stTextInput input, .stSelectbox select {
        background-color: #282828 !important;
        color: #FFFFFF !important;
        border: 1px solid #404040 !important;
        border-radius: 4px;
    }
    
    /* Radio buttons */
    .stRadio > label {
        color: #FFFFFF !important;
    }
    
    /* Expanders - dark theme */
    div[data-testid="stExpander"] {
        background-color: #181818 !important;
        border: 1px solid #282828 !important;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    div[data-testid="stExpander"] p {
        color: #B3B3B3 !important;
    }
    
    /* Dataframes */
    .stDataFrame {
        background-color: #181818 !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: #1DB954 !important;
    }
    
    /* Progress indicators */
    .stProgress > div > div {
        background-color: #1DB954 !important;
    }
    
    /* Info/Success/Warning boxes */
    .stAlert {
        background-color: #181818 !important;
        border-left: 4px solid #1DB954 !important;
        color: #FFFFFF !important;
    }
    
    /* Spinners */
    .stSpinner > div {
        border-top-color: #1DB954 !important;
    }
    
    /* Captions */
    .css-1dp5vir {
        color: #B3B3B3 !important;
    }
    
    /* Horizontal rule */
    hr {
        border-color: #282828 !important;
    }
</style>
""", unsafe_allow_html=True)


class AppState:
    """Manages application state across steps."""
    
    STATE_FILE = ".cache/app_state.json"
    
    @classmethod
    def load(cls) -> Dict:
        """Load app state from cache."""
        if os.path.exists(cls.STATE_FILE):
            try:
                with open(cls.STATE_FILE, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "current_step": 1,
            "source": "liked",
            "playlist_id": "",
            "tracks_fetched": False,
            "tracks_count": 0,
            "classified": False,
            "classifications_count": 0,
            "approved": False,
            "last_updated": None
        }
    
    @classmethod
    def save(cls, state: Dict):
        """Save app state to cache."""
        os.makedirs(".cache", exist_ok=True)
        state["last_updated"] = datetime.now().isoformat()
        with open(cls.STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)


def init_session_state():
    """Initialize Streamlit session state."""
    if 'app_state' not in st.session_state:
        st.session_state.app_state = AppState.load()
    if 'cache_manager' not in st.session_state:
        st.session_state.cache_manager = CacheManager()
    if 'tracks' not in st.session_state:
        st.session_state.tracks = []
    if 'categorized_tracks' not in st.session_state:
        st.session_state.categorized_tracks = {}


def render_header():
    """Render app header."""
    st.markdown("# 🎵 Spotify Organizer")
    st.markdown("*Organize your music with AI*")
    st.markdown("---")


def render_progress_indicator():
    """Render progress steps indicator."""
    state = st.session_state.app_state
    current = state.get("current_step", 1)
    
    cols = st.columns(3)
    
    steps = [
        ("1. Fetch", state.get("tracks_fetched", False)),
        ("2. Classify", state.get("classified", False)),
        ("3. Apply", state.get("approved", False))
    ]
    
    for idx, (col, (label, complete)) in enumerate(zip(cols, steps), 1):
        with col:
            if complete:
                st.success(f"✅ {label}")
            elif idx == current:
                st.info(f"▶️ {label}")
            else:
                st.markdown(f"⚪ {label}")


def step_1_fetch():
    """Step 1: Fetch tracks from Spotify."""
    st.markdown("## Step 1: Fetch Tracks")
    
    with st.form("fetch_form"):
        source = st.radio("Source", ["Liked Songs", "Playlist"], horizontal=True)
        
        playlist_id = ""
        if source == "Playlist":
            playlist_id = st.text_input("Playlist ID", 
                                       help="Enter the Spotify playlist ID")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            fetch_button = st.form_submit_button("🔄 Fetch Tracks", use_container_width=True)
        with col2:
            clear_cache = st.form_submit_button("🗑️ Clear Cache", use_container_width=True)
    
    if clear_cache:
        st.session_state.cache_manager.clear_tracks_cache()
        st.success("✅ Track cache cleared!")
        st.session_state.app_state["tracks_fetched"] = False
        AppState.save(st.session_state.app_state)
        st.rerun()
    
    if fetch_button:
        if source == "Playlist" and not playlist_id:
            st.error("❌ Please enter a Playlist ID")
            return
        
        with st.spinner("🔄 Connecting to Spotify..."):
            try:
                spotify = SpotifyClient()
                user = spotify.get_current_user()
                st.info(f"👤 Logged in as: **{user['display_name']}**")
            except Exception as e:
                st.error(f"❌ Spotify authentication failed: {e}")
                return
        
        # Check cache first
        cache_manager = st.session_state.cache_manager
        source_type = "liked" if source == "Liked Songs" else "playlist"
        source_id = user['id'] if source == "Liked Songs" else playlist_id
        
        cached_session = cache_manager.get_fetch_session(source_type, source_id)
        tracks = None
        
        if cached_session:
            st.info(f"📦 Found cached session from {cached_session['fetched_at'][:10]}")
            track_ids = cached_session['track_ids']
            tracks = cache_manager.get_cached_tracks_by_ids(track_ids)
            
            if len(tracks) == len(track_ids):
                st.success("✅ Using 100% cached track data")
            else:
                tracks = None
        
        if not tracks:
            with st.spinner("📥 Fetching tracks from Spotify..."):
                try:
                    if source == "Liked Songs":
                        tracks = spotify.get_liked_songs()
                    else:
                        tracks = spotify.get_playlist_tracks(playlist_id)
                    
                    # Save to cache
                    cache_manager.save_tracks_batch(tracks)
                    track_ids = [t['id'] for t in tracks]
                    cache_manager.save_fetch_session(source_type, source_id, track_ids)
                    
                except Exception as e:
                    st.error(f"❌ Failed to fetch tracks: {e}")
                    return
        
        # Update state
        st.session_state.tracks = tracks
        st.session_state.app_state.update({
            "current_step": 2,
            "source": source_type,
            "playlist_id": playlist_id if source == "Playlist" else "",
            "tracks_fetched": True,
            "tracks_count": len(tracks)
        })
        AppState.save(st.session_state.app_state)
        
        st.success(f"✅ Loaded **{len(tracks)}** tracks!")
        
        # Show preview
        if tracks:
            with st.expander("📋 Track Preview", expanded=False):
                preview_data = []
                for t in tracks[:10]:
                    preview_data.append({
                        "Title": t.get('name', 'Unknown'),
                        "Artist": ', '.join(t.get('artists', [])),
                        "Album": t.get('album', 'Unknown')
                    })
                st.dataframe(preview_data, use_container_width=True, hide_index=True)
                if len(tracks) > 10:
                    st.caption(f"Showing 10 of {len(tracks)} tracks")
        
        st.rerun()


def step_2_classify():
    """Step 2: Classify tracks with AI."""
    st.markdown("## Step 2: Classify with AI")
    
    state = st.session_state.app_state
    cache_manager = st.session_state.cache_manager
    
    # Load tracks if not in session
    if not st.session_state.tracks:
        source_type = state.get("source", "liked")
        # Try to load from cache
        if state.get("tracks_fetched"):
            st.info("📦 Loading tracks from cache...")
            # Get the cached session
            cached_sessions = cache_manager.fetch_sessions
            matching_session = None
            for key, session in cached_sessions.items():
                if source_type in key:
                    matching_session = session
                    break
            
            if matching_session:
                track_ids = matching_session['track_ids']
                tracks = cache_manager.get_cached_tracks_by_ids(track_ids)
                st.session_state.tracks = tracks
                st.success(f"✅ Loaded {len(tracks)} tracks from cache")
            else:
                st.warning("⚠️ No cached tracks found. Please go back to Step 1.")
                return
        else:
            st.warning("⚠️ No tracks available. Please complete Step 1 first.")
            if st.button("← Go to Step 1"):
                st.session_state.app_state["current_step"] = 1
                AppState.save(st.session_state.app_state)
                st.rerun()
            return
    
    tracks = st.session_state.tracks
    st.info(f"📊 **{len(tracks)}** tracks ready for classification")
    
    # Check what's already classified
    all_track_ids = [t['id'] for t in tracks]
    unclassified_ids = cache_manager.get_unclassified_tracks(all_track_ids)
    already_classified = len(tracks) - len(unclassified_ids)
    
    if already_classified > 0:
        st.success(f"✅ {already_classified} tracks already classified (cached)")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        classify_button = st.button("🤖 Classify Tracks", 
                                    disabled=len(unclassified_ids) == 0,
                                    use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear Classifications", use_container_width=True)
    
    if clear_button:
        cache_manager.clear_classifications_cache()
        st.success("✅ Classifications cleared!")
        st.session_state.app_state["classified"] = False
        AppState.save(st.session_state.app_state)
        st.rerun()
    
    if classify_button:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        classifier = LLMClassifier()
        
        # Get tracks that need classification
        tracks_to_classify = [t for t in tracks if t['id'] in unclassified_ids]
        
        with st.spinner(f"🤖 Classifying {len(tracks_to_classify)} tracks..."):
            try:
                results = classifier.classify_batch(tracks_to_classify)
                
                # Save classifications
                for i, (category, confidence) in enumerate(results):
                    track = tracks_to_classify[i]
                    track['classification_category'] = category
                    track['classification_confidence'] = confidence
                    cache_manager.save_classification(track['id'], category, confidence)
                    
                    progress = (i + 1) / len(tracks_to_classify)
                    progress_bar.progress(progress)
                    status_text.text(f"Classified {i + 1}/{len(tracks_to_classify)} tracks")
                
                st.success(f"✅ Classified {len(tracks_to_classify)} tracks!")
                
                # Update state
                st.session_state.app_state.update({
                    "current_step": 2,
                    "classified": True,
                    "classifications_count": len(tracks)
                })
                AppState.save(st.session_state.app_state)
                
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Classification failed: {e}")
                return
    
    # Show classifications if available
    if state.get("classified") or already_classified > 0:
        st.markdown("---")
        st.markdown("### 📋 Classification Results")
        
        # Load all classifications
        categorized = {}
        for track in tracks:
            track_id = track['id']
            cached_class = cache_manager.get_classification(track_id)
            
            if cached_class:
                category = cached_class['category']
                confidence = cached_class.get('confidence', 0.8)
            else:
                category = "Unclassified"
                confidence = 0.0
            
            track['classification_category'] = category
            track['classification_confidence'] = confidence
            
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(track)
        
        st.session_state.categorized_tracks = categorized
        
        # Summary stats
        cols = st.columns(4)
        cols[0].metric("Total Tracks", len(tracks))
        cols[1].metric("Categories", len(categorized))
        cols[2].metric("Classified", sum(len(v) for k, v in categorized.items() if k != "Unclassified"))
        cols[3].metric("Avg Confidence", f"{sum(t.get('classification_confidence', 0) for t in tracks) / len(tracks):.0%}")
        
        # Category breakdown with editable classifications
        st.markdown("#### Edit Classifications")
        
        for category in sorted(categorized.keys(), key=lambda k: len(categorized[k]), reverse=True):
            tracks_in_cat = categorized[category]
            
            with st.expander(f"**{category}** ({len(tracks_in_cat)} tracks)", expanded=False):
                for idx, track in enumerate(tracks_in_cat):
                    col1, col2, col3 = st.columns([3, 2, 1])
                    
                    with col1:
                        st.markdown(f"**{track['name']}**")
                        st.caption(f"{', '.join(track['artists'][:2])}")
                    
                    with col2:
                        new_category = st.selectbox(
                            "Category",
                            options=Config.CATEGORIES,
                            index=Config.CATEGORIES.index(category) if category in Config.CATEGORIES else 0,
                            key=f"cat_{track['id']}",
                            label_visibility="collapsed"
                        )
                        
                        if new_category != category:
                            # Update classification
                            confidence = track.get('classification_confidence', 0.8)
                            cache_manager.save_classification(track['id'], new_category, confidence)
                            st.success("✅ Updated!")
                            st.rerun()
                    
                    with col3:
                        confidence_pct = track.get('classification_confidence', 0) * 100
                        st.metric("Confidence", f"{confidence_pct:.0f}%")
        
        # Approve button
        st.markdown("---")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("✅ Approve & Continue to Step 3", use_container_width=True, type="primary"):
                # Save review file
                review_file = ReviewManager.save_for_review(
                    categorized, 
                    "Liked Songs" if state.get("source") == "liked" else f"Playlist {state.get('playlist_id')}"
                )
                
                # Mark as approved
                review_data = ReviewManager.load_review()
                review_data["approved"] = True
                with open(ReviewManager.REVIEW_FILE, 'w', encoding='utf-8') as f:
                    json.dump(review_data, f, indent=2, ensure_ascii=False)
                
                st.session_state.app_state.update({
                    "current_step": 3,
                    "approved": True
                })
                AppState.save(st.session_state.app_state)
                st.success("✅ Classifications approved!")
                st.rerun()
        
        with col2:
            if st.button("📥 Export to JSON", use_container_width=True):
                review_file = ReviewManager.save_for_review(
                    categorized,
                    "Liked Songs" if state.get("source") == "liked" else f"Playlist {state.get('playlist_id')}"
                )
                st.success(f"✅ Exported to {review_file}")


def step_3_apply():
    """Step 3: Apply classifications to Spotify playlists."""
    st.markdown("## Step 3: Apply to Playlists")
    
    if not ReviewManager.is_approved():
        st.warning("⚠️ Classifications not approved yet. Please complete Step 2.")
        if st.button("← Go to Step 2"):
            st.session_state.app_state["current_step"] = 2
            AppState.save(st.session_state.app_state)
            st.rerun()
        return
    
    review_data = ReviewManager.load_review()
    
    st.info(f"📋 Review approved on {review_data['timestamp'][:10]}")
    st.metric("Total Tracks", review_data['total_tracks'])
    
    # Show summary
    st.markdown("### 📊 Playlists to Create/Update")
    
    summary_data = []
    for category, data in review_data['categories'].items():
        summary_data.append({
            "Category": category,
            "Tracks": data['count']
        })
    
    st.dataframe(summary_data, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🎵 Create/Update Playlists", use_container_width=True, type="primary"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Initialize Spotify
                with st.spinner("🔄 Connecting to Spotify..."):
                    spotify = SpotifyClient()
                    user = spotify.get_current_user()
                    st.info(f"👤 Connected as: {user['display_name']}")
                
                # Reconstruct categorized tracks
                categorized_tracks = {}
                for category, data in review_data['categories'].items():
                    categorized_tracks[category] = data['tracks']
                
                # Create playlists
                playlist_manager = PlaylistManager(spotify)
                total_categories = len(categorized_tracks)
                
                for idx, (category, tracks) in enumerate(categorized_tracks.items()):
                    status_text.text(f"Creating playlist: {category}...")
                    
                    # This will be handled by PlaylistManager
                    # Just showing progress here
                    
                    progress = (idx + 1) / total_categories
                    progress_bar.progress(progress)
                
                # Actually create the playlists
                playlist_manager.create_categorized_playlists(categorized_tracks, review_data['source'])
                
                st.success("✅ All playlists created/updated successfully!")
                st.balloons()
                
                # Reset state for next run
                if st.button("🔄 Start Over"):
                    st.session_state.app_state = {
                        "current_step": 1,
                        "tracks_fetched": False,
                        "classified": False,
                        "approved": False
                    }
                    AppState.save(st.session_state.app_state)
                    st.rerun()
                
            except Exception as e:
                st.error(f"❌ Failed to create playlists: {e}")
                import traceback
                st.code(traceback.format_exc())
    
    with col2:
        if st.button("← Back to Step 2", use_container_width=True):
            st.session_state.app_state["current_step"] = 2
            AppState.save(st.session_state.app_state)
            st.rerun()


def main():
    """Main Streamlit app."""
    init_session_state()
    
    render_header()
    render_progress_indicator()
    
    st.markdown("---")
    
    # Step navigation
    state = st.session_state.app_state
    current_step = state.get("current_step", 1)
    
    # Sidebar for navigation and info
    with st.sidebar:
        st.markdown("### 🎯 Navigation")
        
        step = st.radio(
            "Jump to Step",
            options=[1, 2, 3],
            format_func=lambda x: ["1. Fetch Tracks", "2. Classify", "3. Apply"][x-1],
            index=current_step - 1,
            key="step_nav"
        )
        
        if step != current_step:
            st.session_state.app_state["current_step"] = step
            AppState.save(st.session_state.app_state)
            st.rerun()
        
        st.markdown("---")
        st.markdown("### ℹ️ Info")
        st.caption(f"**Tracks Fetched:** {state.get('tracks_count', 0)}")
        st.caption(f"**Classified:** {'✅' if state.get('classified') else '❌'}")
        st.caption(f"**Approved:** {'✅' if state.get('approved') else '❌'}")
        
        if state.get('last_updated'):
            st.caption(f"**Last Updated:** {state['last_updated'][:10]}")
        
        st.markdown("---")
        st.markdown("### ⚙️ Settings")
        if st.button("🗑️ Clear All Data", use_container_width=True):
            cache_manager = st.session_state.cache_manager
            cache_manager.clear_cache()
            st.session_state.app_state = AppState.load()
            st.success("✅ All data cleared!")
            st.rerun()
    
    # Render current step
    if current_step == 1:
        step_1_fetch()
    elif current_step == 2:
        step_2_classify()
    elif current_step == 3:
        step_3_apply()


if __name__ == "__main__":
    main()
