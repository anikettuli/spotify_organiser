#!/usr/bin/env python3
"""
Test script to fetch and analyze a small sample (100 tracks) from liked songs.
This avoids rate limits and lets us see what data we're working with.
"""
import json
from spotify_client import SpotifyClient
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from collections import Counter
import config

console = Console()

def fetch_small_sample():
    """Fetch just 100 tracks from liked songs."""
    
    console.print(Panel("[bold cyan]🎵 FETCHING 100 SAMPLE TRACKS[/bold cyan]"))
    
    # Initialize Spotify client
    console.print("\n🔐 Authenticating with Spotify...", style="cyan")
    console.print(f"[dim]  USE_MOCKS={config.Config.USE_MOCKS}[/dim]")
    console.print(f"[dim]  CLIENT_ID={'set' if config.Config.SPOTIFY_CLIENT_ID else 'not set'}[/dim]")
    
    client = SpotifyClient()
    
    # Check if authentication succeeded
    if client.sp is None:
        console.print("[red]❌ Authentication failed or running in mock mode[/red]")
        console.print("[yellow]Make sure USE_MOCKS=0 in .env and you're authenticated[/yellow]")
        console.print(f"[dim]  Debug: sp is None, checking why...[/dim]")
        
        # Check if spotipy is available
        try:
            import spotipy
            console.print("[dim]  spotipy module: ✓ Available[/dim]")
        except:
            console.print("[red]  spotipy module: ✗ Not installed[/red]")
        
        return []
    
    # Get current user to confirm connection
    try:
        user = client.sp.current_user()
        console.print(f"[green]✓ Authenticated as: {user.get('display_name', 'Unknown')}[/green]")
    except Exception as e:
        console.print(f"[red]❌ Connection test failed: {e}[/red]")
        return []
    
    # Fetch tracks (limit to 100)
    console.print("📥 Fetching 100 tracks...", style="cyan")
    
    all_tracks = []
    offset = 0
    limit = 50  # Spotify API limit per request
    
    while len(all_tracks) < 100:
        try:
            results = client.sp.current_user_saved_tracks(limit=limit, offset=offset)
            items = results.get('items', [])
            
            if not items:
                break
            
            for item in items:
                track_data = item.get('track', {})
                if track_data:
                    track_info = {
                        'id': track_data.get('id'),
                        'name': track_data.get('name'),
                        'artists': [artist['name'] for artist in track_data.get('artists', [])],
                        'artist_ids': [artist['id'] for artist in track_data.get('artists', [])],
                        'album': track_data.get('album', {}).get('name'),
                        'release_date': track_data.get('album', {}).get('release_date'),
                        'markets': track_data.get('available_markets', []),
                        'genres': []  # Will be populated below
                    }
                    all_tracks.append(track_info)
                    
                    if len(all_tracks) >= 100:
                        break
            
            offset += limit
            console.print(f"  Fetched {len(all_tracks)} tracks so far...", style="dim")
            
        except Exception as e:
            console.print(f"[red]Error fetching tracks: {e}[/red]")
            break
    
    console.print(f"[green]✓ Fetched {len(all_tracks)} tracks[/green]")
    
    # Get unique artists
    console.print("\n🎤 Collecting unique artists...", style="cyan")
    unique_artist_ids = set()
    for track in all_tracks:
        unique_artist_ids.update(track['artist_ids'])
    
    console.print(f"[green]✓ Found {len(unique_artist_ids)} unique artists[/green]")
    console.print(f"[dim]  (avoided {len([a for t in all_tracks for a in t['artist_ids']]) - len(unique_artist_ids)} duplicate API calls)[/dim]")
    
    # Fetch artist genres (if enabled)
    if config.Config.FETCH_ARTIST_GENRES:
        console.print("\n🎸 Fetching artist genres with optimized batching...", style="cyan")
        
        artist_genres = {}
        artist_ids_list = list(unique_artist_ids)
        
        # Test different batch sizes to find optimal
        # Spotify allows up to 50 artists per request
        # Smaller batches = more API calls but faster individual requests
        # Larger batches = fewer API calls but slower, more likely to hit rate limits
        
        batch_size = 50  # Maximum allowed by Spotify API
        delay_between_batches = 0.3  # Start with shorter delay (was 0.5s)
        
        console.print(f"[dim]  Strategy: {batch_size} artists/batch, {delay_between_batches}s delay[/dim]")
        console.print(f"[dim]  Total batches needed: {(len(artist_ids_list) + batch_size - 1) // batch_size}[/dim]")
        
        try:
            import time
            successful_batches = 0
            failed_batches = 0
            
            for i in range(0, len(artist_ids_list), batch_size):
                batch = artist_ids_list[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                total_batches = (len(artist_ids_list) + batch_size - 1) // batch_size
                
                try:
                    start_time = time.time()
                    artists_response = client.sp.artists(batch)
                    request_time = time.time() - start_time
                    
                    for artist in artists_response.get('artists', []):
                        if artist:
                            artist_genres[artist['id']] = artist.get('genres', [])
                    
                    successful_batches += 1
                    console.print(
                        f"  ✓ Batch {batch_num}/{total_batches}: "
                        f"{len(batch)} artists in {request_time:.2f}s | "
                        f"Total: {len(artist_genres)}/{len(artist_ids_list)}",
                        style="dim"
                    )
                    
                    # Adaptive delay: if request was slow, increase delay slightly
                    if request_time > 1.0:
                        delay_between_batches = min(delay_between_batches * 1.2, 2.0)
                        console.print(f"  [yellow]Slow response, increasing delay to {delay_between_batches:.2f}s[/yellow]")
                    
                    # Delay between batches
                    if i + batch_size < len(artist_ids_list):
                        time.sleep(delay_between_batches)
                
                except Exception as e:
                    failed_batches += 1
                    error_msg = str(e).lower()
                    
                    if 'rate' in error_msg or '429' in error_msg:
                        console.print(f"  [red]✗ Rate limit hit at batch {batch_num}[/red]")
                        console.print(f"  [yellow]Successfully fetched genres for {len(artist_genres)} artists before rate limit[/yellow]")
                        break
                    else:
                        console.print(f"  [yellow]⚠️  Batch {batch_num} failed: {e}[/yellow]")
                        continue
            
            # Map genres back to tracks
            for track in all_tracks:
                track_genres = []
                for artist_id in track['artist_ids']:
                    track_genres.extend(artist_genres.get(artist_id, []))
                track['genres'] = list(set(track_genres))  # Remove duplicates
            
            tracks_with_genres = sum(1 for t in all_tracks if t['genres'])
            
            console.print(f"\n[bold]Fetch Summary:[/bold]")
            console.print(f"  Successful batches: {successful_batches}")
            console.print(f"  Failed batches: {failed_batches}")
            console.print(f"  Artists with genre data: {len(artist_genres)}/{len(artist_ids_list)}")
            console.print(f"  Tracks enriched: {tracks_with_genres}/{len(all_tracks)}")
            
            if tracks_with_genres > 0:
                console.print(f"[green]✓ Successfully enriched {tracks_with_genres}/{len(all_tracks)} tracks ({tracks_with_genres/len(all_tracks)*100:.1f}%)[/green]")
            else:
                console.print(f"[yellow]⚠️  No tracks enriched - likely hit rate limit immediately[/yellow]")
            
        except Exception as e:
            console.print(f"[yellow]⚠️  Genre fetching error: {e}[/yellow]")
            console.print("[dim]  Continuing with available data...[/dim]")
    else:
        console.print("\n⏭️  Skipping artist genre fetching (disabled in config)", style="yellow")
    
    return all_tracks


def analyze_tracks(tracks):
    """Analyze and display track information."""
    
    console.print(f"\n{Panel('[bold yellow]📊 DATA ANALYSIS[/bold yellow]')}")
    
    # Basic statistics
    console.print(f"\n[bold]Overview:[/bold]")
    console.print(f"  Total tracks: {len(tracks)}")
    
    # Artist analysis
    all_artists = []
    for track in tracks:
        all_artists.extend(track['artists'])
    
    artist_counts = Counter(all_artists)
    console.print(f"  Unique artists: {len(set(all_artists))}")
    console.print(f"  Total artist references: {len(all_artists)}")
    console.print(f"  Avg artists per track: {len(all_artists) / len(tracks):.2f}")
    
    # Genre analysis
    all_genres = []
    tracks_with_genres = 0
    for track in tracks:
        if track['genres']:
            tracks_with_genres += 1
            all_genres.extend(track['genres'])
    
    console.print(f"  Tracks with genres: {tracks_with_genres}/{len(tracks)} ({tracks_with_genres/len(tracks)*100:.1f}%)")
    console.print(f"  Unique genres: {len(set(all_genres))}")
    
    # Year analysis
    years = []
    for track in tracks:
        date = track.get('release_date', '')
        if date and len(date) >= 4:
            try:
                years.append(int(date[:4]))
            except:
                pass
    
    if years:
        console.print(f"  Year range: {min(years)} - {max(years)}")
        oldies_count = sum(1 for y in years if y < 2000)
        console.print(f"  Pre-2000 tracks: {oldies_count}")
    
    # Top artists
    console.print(f"\n[bold]🎤 Top 20 Artists:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Artist", style="cyan", width=40)
    table.add_column("Tracks", justify="right", style="green")
    
    for i, (artist, count) in enumerate(artist_counts.most_common(20), 1):
        table.add_row(str(i), artist[:40], str(count))
    
    console.print(table)
    
    # Top genres
    if all_genres:
        genre_counts = Counter(all_genres)
        console.print(f"\n[bold]🎸 Top 20 Genres:[/bold]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Genre", style="cyan", width=40)
        table.add_column("Count", justify="right", style="green")
        
        for i, (genre, count) in enumerate(genre_counts.most_common(20), 1):
            table.add_row(str(i), genre[:40], str(count))
        
        console.print(table)
    
    # Sample tracks
    console.print(f"\n[bold]🎵 First 20 Tracks:[/bold]")
    table = Table(show_header=True, header_style="bold magenta", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Track", style="cyan", width=30)
    table.add_column("Artists", style="yellow", width=30)
    table.add_column("Year", width=6)
    table.add_column("Genres", style="green", width=25)
    
    for i, track in enumerate(tracks[:20], 1):
        name = track['name'][:30]
        artists = ", ".join(track['artists'])[:30]
        year = track.get('release_date', '')[:4] if track.get('release_date') else 'N/A'
        genres = ", ".join(track['genres'][:2])[:25] if track['genres'] else 'None'
        table.add_row(str(i), name, artists, year, genres)
    
    console.print(table)


def save_to_file(tracks):
    """Save tracks to JSON file."""
    
    output_file = 'sample_100_tracks.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tracks, f, indent=2, ensure_ascii=False)
    
    console.print(f"\n[green]✅ Saved {len(tracks)} tracks to: {output_file}[/green]")
    
    # Also create a detailed text report
    report_file = 'sample_100_tracks_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("100 SAMPLE TRACKS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total tracks: {len(tracks)}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("ALL TRACKS\n")
        f.write("=" * 80 + "\n")
        for i, track in enumerate(tracks, 1):
            f.write(f"\n{i}. {track['name']}\n")
            f.write(f"   Artists: {', '.join(track['artists'])}\n")
            f.write(f"   Album: {track['album']}\n")
            f.write(f"   Year: {track.get('release_date', 'N/A')}\n")
            f.write(f"   Genres: {', '.join(track['genres']) or 'None'}\n")
            f.write(f"   Markets: {len(track.get('markets', []))} countries\n")
            f.write("-" * 80 + "\n")
    
    console.print(f"[green]✅ Saved detailed report to: {report_file}[/green]")


def main():
    """Main function."""
    try:
        # Fetch sample tracks
        tracks = fetch_small_sample()
        
        if not tracks:
            console.print("[red]No tracks fetched. Please check your Spotify connection.[/red]")
            return
        
        # Analyze tracks
        analyze_tracks(tracks)
        
        # Save to files
        save_to_file(tracks)
        
        console.print("\n" + "=" * 80)
        console.print("[bold green]✅ Sample data collection complete![/bold green]")
        console.print("=" * 80)
        
        console.print("\n[bold cyan]Next steps:[/bold cyan]")
        console.print("  1. Review 'sample_100_tracks.json' to see the raw data")
        console.print("  2. Review 'sample_100_tracks_report.txt' for detailed track info")
        console.print("  3. You can now test classification on this small dataset!")
        
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
