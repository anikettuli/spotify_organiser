#!/usr/bin/env python3
"""Main CLI interface for Spotify LLM Organizer."""
import argparse
import sys
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from spotify_client import SpotifyClient
from classifier import SongClassifier
from playlist_manager import PlaylistManager
from cache_manager import CacheManager
from config import Config


console = Console()


def print_banner():
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════╗
║     🎵 Spotify LLM Organizer 🎵                  ║
║     Organize your music with AI                   ║
╚═══════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def print_summary(categorized_tracks: dict, cache_stats: dict = None):
    """Print classification summary."""
    table = Table(title="Classification Summary", show_header=True, header_style="bold magenta")
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Tracks", justify="right", style="green")
    
    total = 0
    for category in Config.CATEGORIES:
        count = len(categorized_tracks.get(category, []))
        table.add_row(category, str(count))
        total += count
    
    table.add_row("─" * 20, "─" * 10, style="dim")
    table.add_row("TOTAL", str(total), style="bold")
    
    console.print()
    console.print(table)
    
    if cache_stats:
        console.print()
        console.print(f"📦 Cache Stats: {cache_stats['tracks_cached']} tracks, "
                     f"{cache_stats['classifications_cached']} classifications cached",
                     style="dim")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Organize Spotify songs into categorized playlists using AI"
    )
    parser.add_argument(
        '--source',
        choices=['liked', 'playlist'],
        required=True,
        help='Source of tracks (liked songs or specific playlist)'
    )
    parser.add_argument(
        '--playlist-id',
        help='Playlist ID (required if source is playlist)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview classification without creating playlists'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Clear all cached data before running'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.source == 'playlist' and not args.playlist_id:
        console.print("❌ Error: --playlist-id is required when source is 'playlist'", style="bold red")
        sys.exit(1)
    
    print_banner()
    
    try:
        # --- STEP 1: CONFIGURATION & CACHE ---
        console.print(Panel("[bold cyan]STEP 1/5: CONFIGURATION & CACHE[/bold cyan]"))
        
        # Validate configuration
        Config.validate()
        console.print("✅ Configuration validated")
        
        # Initialize cache manager
        cache_manager = CacheManager()
        
        if args.clear_cache:
            console.print("🗑️  Clearing cache...", style="yellow")
            cache_manager.clear_cache()
            console.print("✅ Cache cleared")
        
        # --- STEP 2: SPOTIFY AUTHENTICATION ---
        console.print(Panel("[bold cyan]STEP 2/5: SPOTIFY AUTHENTICATION[/bold cyan]"))
        try:
            spotify = SpotifyClient()
            user = spotify.get_current_user()
            console.print(f"✅ Logged in as: {user['display_name']}", style="green")
        except Exception as e:
            if "403" in str(e) or "Forbidden" in str(e):
                console.print("\n❌ Spotify Authentication Failed (403 Forbidden)", style="bold red")
                console.print("\n📝 Your Spotify app is in Development Mode. You need to add yourself as a user:", style="yellow")
                console.print("\n   1. Go to: https://developer.spotify.com/dashboard", style="cyan")
                console.print("   2. Click on your app", style="cyan")
                console.print("   3. Go to Settings → User Management", style="cyan")
                console.print("   4. Click 'Add New User'", style="cyan")
                console.print("   5. Enter your Spotify email address", style="cyan")
                console.print("   6. Save and try running the app again\n", style="cyan")
                raise
            else:
                raise
        
        # --- STEP 3: FETCH TRACKS ---
        console.print(Panel("[bold cyan]STEP 3/5: FETCH TRACKS[/bold cyan]"))
        
        # Determine source ID for session tracking
        if args.source == 'liked':
            source_id = user['id']
            source_name = "Liked Songs"
        else:
            source_id = args.playlist_id
            source_name = spotify.get_playlist_name(args.playlist_id)
        
        # Check if we have a cached session
        cached_session = cache_manager.get_fetch_session(args.source, source_id)
        tracks = None
        
        if cached_session:
            console.print(f"📦 Found cached session from {cached_session['fetched_at'][:10]} for '{source_name}'", style="yellow")
            track_ids = cached_session['track_ids']
            tracks = cache_manager.get_cached_tracks_by_ids(track_ids)
            
            if len(tracks) == len(track_ids):
                console.print("✅ Using 100% cached track data (no Spotify API calls needed)", style="green")
            else:
                console.print("⚠️  Some cached tracks missing, re-fetching from Spotify...", style="yellow")
                tracks = None
        
        # Fetch from Spotify if not fully cached
        if not tracks:
            if args.source == 'liked':
                console.print("📥 Fetching liked songs from Spotify...", style="cyan")
                with console.status("[bold cyan]⏳ Loading tracks from Spotify API..."):
                    tracks = spotify.get_liked_songs()
            else:
                console.print(f"📥 Fetching playlist '{source_name}' from Spotify...", style="cyan")
                with console.status("[bold cyan]⏳ Loading tracks from Spotify API..."):
                    tracks = spotify.get_playlist_tracks(args.playlist_id)
            
            console.print(f"\n✅ Loaded {len(tracks)} tracks from {source_name}", style="green")
            
            # Show statistics
            unique_artists = set()
            for t in tracks:
                unique_artists.update(t.get('artists', []))
            
            tracks_with_genres = sum(1 for t in tracks if t.get('genres'))
            total_genres = sum(len(t.get('genres', [])) for t in tracks)
            
            console.print(f"   🎤 {len(unique_artists)} unique artists", style="dim")
            console.print(f"   🎸 {tracks_with_genres}/{len(tracks)} tracks have genre data ({total_genres} total genres)", style="dim")
            
            # Save to cache
            console.print("💾 Saving tracks to cache...", style="dim")
            cache_manager.save_tracks_batch(tracks)
            track_ids = [t['id'] for t in tracks]
            cache_manager.save_fetch_session(args.source, source_id, track_ids)
            console.print("✅ All Spotify data safely cached", style="green")
        
        # --- STEP 4: CLASSIFY TRACKS ---
        console.print(Panel("[bold cyan]STEP 4/5: CLASSIFY TRACKS[/bold cyan]"))
        
        # Check which tracks still need classification
        all_track_ids = [t['id'] for t in tracks]
        unclassified_ids = cache_manager.get_unclassified_tracks(all_track_ids)
        
        if len(unclassified_ids) < len(tracks):
            already_classified = len(tracks) - len(unclassified_ids)
            console.print(f"📊 {already_classified} of {len(tracks)} tracks already classified (from cache)", style="green")
        
        if not unclassified_ids:
            console.print("✅ No new tracks to classify!", style="bold green")
            # Load all classifications from cache for summary
            categorized_tracks = {}
            for track in tracks:
                category = cache_manager.get_classification(track['id']) or 'Misc'
                if category not in categorized_tracks:
                    categorized_tracks[category] = []
                categorized_tracks[category].append(track)
        else:
            console.print(f"🤖 Classifying {len(unclassified_ids)} new tracks with AI...", style="cyan")
            
            # Initialize classifier
            classifier = SongClassifier()
            
            # Classify tracks with error handling and real-time output
            try:
                console.print()
                console.print("═" * 80, style="dim")
                console.print("🎵 TRACK-BY-TRACK CLASSIFICATION", style="bold cyan")
                console.print("═" * 80, style="dim")
                
                def track_update(track, category, processed, total):
                    """Callback for each track completion."""
                    artists = ", ".join(track.get('artists', ['Unknown']))
                    name = track.get('name', 'Unknown')
                    
                    # Category color coding
                    category_colors = {
                        'English': 'blue', 'Hindi': 'magenta', 'Punjabi': 'yellow',
                        'Phonk/Instrumental': 'cyan', 'Oldies': 'green', 'Misc': 'red'
                    }
                    color = category_colors.get(category, 'white')
                    
                    console.print(f"[{processed:4d}/{total}] [{color}]{category:20s}[/{color}] | {artists[:30]:<30s} - {name[:40]:<40s}")
                
                categorized_tracks = classifier.classify_tracks(tracks, track_callback=track_update)
                
                console.print("═" * 80, style="dim")
                console.print("✅ Classification complete!", style="bold green")
                
                # Show low confidence warnings
                low_conf_tracks = [t for t in tracks if t.get('_low_confidence_guess')]
                if low_conf_tracks:
                    console.print(f"\n⚠️  {len(low_conf_tracks)} tracks had <80% confidence and were moved to 'Misc':", style="yellow")
                    for t in low_conf_tracks[:5]:  # Show first 5
                        guess = t.get('_low_confidence_guess', '')
                        console.print(f"   • {t.get('name')} - {', '.join(t.get('artists', []))} (guessed: {guess})", style="dim")
                    if len(low_conf_tracks) > 5:
                        console.print(f"   ... and {len(low_conf_tracks) - 5} more", style="dim")
            
            except KeyboardInterrupt:
                console.print("\n⚠️  Classification interrupted!", style="yellow")
                console.print("💾 Progress has been saved to cache. Run again to resume.", style="green")
                sys.exit(0)
            except Exception as e:
                console.print(f"\n❌ Classification error: {e}", style="red")
                console.print("💾 Partial progress saved. Run again to resume.", style="green")
                raise
        
        # --- STEP 5: SUMMARY & PLAYLISTS ---
        console.print(Panel("[bold cyan]STEP 5/5: SUMMARY & PLAYLISTS[/bold cyan]"))
        
        # Print summary
        cache_stats = cache_manager.get_cache_stats()
        print_summary(categorized_tracks, cache_stats)
        
        # Create playlists
        if not args.dry_run:
            console.print()
            console.print("📝 Creating playlists...", style="cyan")
            playlist_manager = PlaylistManager(spotify)
            playlist_ids = playlist_manager.create_categorized_playlists(
                categorized_tracks,
                source_name,
                dry_run=False
            )
            
            console.print()
            console.print(Panel("🎉 All done! Check your Spotify for the new playlists.", style="bold green"))
        else:
            console.print()
            console.print(Panel("📋 [bold yellow]Dry run complete[/bold yellow] - no playlists were created.\nRun without `--dry-run` to create them.", title="Dry Run"))
    
    except ValueError as e:
        console.print(f"❌ Configuration Error: {e}", style="bold red")
        console.print("\n💡 Make sure you have set up your .env file correctly", style="yellow")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n\n⚠️  Interrupted by user", style="yellow")
        sys.exit(0)
    except Exception as e:
        console.print(f"❌ Error: {e}", style="bold red")
        import traceback
        console.print("\n" + traceback.format_exc(), style="dim")
        sys.exit(1)


if __name__ == "__main__":
    main()

