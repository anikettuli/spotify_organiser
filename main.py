#!/usr/bin/env python3
"""Main CLI interface for Spotify LLM Organizer."""
import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from spotify_client import SpotifyClient
from llm_classifier import LLMClassifier
from playlist_manager import PlaylistManager
from cache_manager import CacheManager
from review_manager import ReviewManager
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
    # Workflow commands (mutually exclusive)
    workflow = parser.add_mutually_exclusive_group()
    workflow.add_argument(
        '--fetch',
        action='store_true',
        help='Step 1: Fetch tracks from Spotify (rarely needed)'
    )
    workflow.add_argument(
        '--classify',
        action='store_true',
        help='Step 2: Classify tracks with AI (run often to reclassify)'
    )
    workflow.add_argument(
        '--apply',
        action='store_true',
        help='Step 3: Apply classifications and create/update playlists'
    )
    
    parser.add_argument(
        '--source',
        choices=['liked', 'playlist'],
        default='liked',
        help='Source of tracks (default: liked)'
    )
    parser.add_argument(
        '--playlist-id',
        help='Playlist ID (required if source is playlist)'
    )
    parser.add_argument(
        '--clear-tracks',
        action='store_true',
        help='Clear cached tracks (for --fetch)'
    )
    parser.add_argument(
        '--clear-classifications',
        action='store_true',
        help='Clear cached classifications (for --classify)'
    )
    
    # Legacy support
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Legacy: Run all steps but preview only (same as --classify)'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='Legacy: Clear all cached data'
    )
    
    args = parser.parse_args()
    
    # Determine workflow mode
    if args.fetch or args.classify or args.apply:
        # New workflow mode
        if args.fetch:
            mode = 'fetch'
        elif args.classify:
            mode = 'classify'
        else:
            mode = 'apply'
    elif args.dry_run:
        mode = 'classify'  # Legacy: dry-run is now classify
    else:
        mode = 'all'  # Legacy: run everything
    
    # Validate arguments
    if args.source == 'playlist' and not args.playlist_id:
        console.print("❌ Error: --playlist-id is required when source is 'playlist'", style="bold red")
        sys.exit(1)
    
    print_banner()
    
    # Show workflow mode
    if mode != 'all':
        mode_labels = {
            'fetch': '1️⃣  STEP 1: FETCH TRACKS FROM SPOTIFY',
            'classify': '2️⃣  STEP 2: CLASSIFY TRACKS WITH AI',
            'apply': '3️⃣  STEP 3: APPLY TO PLAYLISTS'
        }
        console.print(f"\n[bold cyan]{mode_labels[mode]}[/bold cyan]\n")
    
    try:
        # --- STEP 1: CONFIGURATION & CACHE ---
        console.print(Panel("[bold cyan]STEP 1/5: CONFIGURATION & CACHE[/bold cyan]"))
        
        # Validate configuration
        Config.validate()
        console.print("✅ Configuration validated")
        
        # Initialize cache manager
        cache_manager = CacheManager()
        
        # Handle cache clearing flags
        if args.clear_cache:
            console.print("🗑️  Clearing all cache...", style="yellow")
            cache_manager.clear_cache()
            console.print("✅ Cache cleared")
        elif args.clear_tracks:
            console.print("🗑️  Clearing track cache only...", style="yellow")
            cache_manager.clear_tracks_cache()
            console.print("✅ Track cache cleared")
        elif args.clear_classifications:
            console.print("🗑️  Clearing classification cache only...", style="yellow")
            cache_manager.clear_classifications_cache()
            console.print("✅ Classification cache cleared")
        
        # --- WORKFLOW BRANCHING ---
        if mode == 'apply':
            # STEP 3: Apply from review file
            console.print("\n[bold]Loading review file...[/bold]")
            
            if not ReviewManager.is_approved():
                console.print("\n❌ [bold red]Review file not approved![/bold red]")
                console.print("\n📝 To approve classifications:")
                console.print("   1. Review: cat .review/classification_review.json")
                console.print("   2. Edit 'approved' field to true")
                console.print("   3. Run again: python main.py --apply\n")
                sys.exit(1)
            
            review_data = ReviewManager.load_review()
            console.print(f"✅ Loaded approved review from {review_data['timestamp'][:10]}")
            console.print(f"   📊 {review_data['total_tracks']} tracks in {len(review_data['categories'])} categories")
            
            # Reconstruct categorized_tracks from review
            categorized_tracks = {}
            for category, data in review_data['categories'].items():
                categorized_tracks[category] = data['tracks']
            
            # Initialize Spotify for playlist operations
            spotify = SpotifyClient()
            user = spotify.get_current_user()
            console.print(f"✅ Logged in as: {user['display_name']}", style="green")
            
            # Create/update playlists
            console.print(Panel("[bold cyan]CREATING/UPDATING PLAYLISTS[/bold cyan]"))
            playlist_manager = PlaylistManager(spotify)
            playlist_manager.create_categorized_playlists(categorized_tracks, review_data['source'])
            
            console.print("\n✅ [bold green]Playlists applied successfully![/bold green]")
            sys.exit(0)
        
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
        
        # Exit after fetch if in fetch-only mode
        if mode == 'fetch':
            console.print("\n✅ [bold green]Tracks fetched and cached![/bold green]")
            console.print(f"\n📝 Next step: python main.py --source {args.source} --classify")
            sys.exit(0)
        
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
            classifier = LLMClassifier()
            
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
        
        # Exit after classification if in classify mode
        if mode == 'classify':
            console.print("\n[bold]Saving classifications for review...[/bold]")
            review_file = ReviewManager.save_for_review(categorized_tracks, source_name)
            
            # Show summary
            console.print(f"\n✅ [bold green]Classifications saved to review file![/bold green]")
            console.print(f"   📁 Location: {review_file}")
            console.print(f"   📊 {len(tracks)} tracks in {len(categorized_tracks)} categories")
            
            # Show category breakdown
            console.print("\n📋 [bold]Category Breakdown:[/bold]")
            for category in sorted(categorized_tracks.keys(), key=lambda k: len(categorized_tracks[k]), reverse=True):
                count = len(categorized_tracks[category])
                pct = (count / len(tracks)) * 100
                console.print(f"   {category:30s}: {count:4d} tracks ({pct:5.1f}%)")
            
            console.print("\n📝 [bold]Next steps:[/bold]")
            console.print("   1. Review: cat .review/classification_review.json")
            console.print("   2. Edit 'approved' field to true when satisfied")
            console.print(f"   3. Apply: python main.py --source {args.source} --apply\n")
            sys.exit(0)
        
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

