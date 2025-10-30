#!/usr/bin/env python3
"""
Fetch 100 sample tracks WITHOUT artist genres to avoid rate limits.
This gives us basic track info to analyze.
"""
import json
from spotify_client import SpotifyClient
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from collections import Counter
import config

console = Console()

def fetch_tracks_no_genres():
    """Fetch 100 tracks without genre data."""
    
    console.print(Panel("[bold cyan]🎵 FETCHING 100 SAMPLE TRACKS (NO GENRES)[/bold cyan]"))
    
    console.print("\n🔐 Authenticating with Spotify...", style="cyan")
    client = SpotifyClient()
    
    if client.sp is None:
        console.print("[red]❌ Authentication failed[/red]")
        return []
    
    user = client.sp.current_user()
    console.print(f"[green]✓ Authenticated as: {user.get('display_name', 'Unknown')}[/green]")
    
    console.print("\n📥 Fetching 100 tracks...", style="cyan")
    
    all_tracks = []
    offset = 0
    limit = 50
    
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
                        'popularity': track_data.get('popularity'),
                        'explicit': track_data.get('explicit'),
                        'duration_ms': track_data.get('duration_ms'),
                        'genres': []  # Will remain empty - no genre fetching
                    }
                    all_tracks.append(track_info)
                    
                    if len(all_tracks) >= 100:
                        break
            
            offset += limit
            console.print(f"  Fetched {len(all_tracks)} tracks", style="dim")
            
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            break
    
    console.print(f"[green]✓ Fetched {len(all_tracks)} tracks successfully![/green]")
    
    # Get unique artist stats
    unique_artist_ids = set()
    for track in all_tracks:
        unique_artist_ids.update(track['artist_ids'])
    
    console.print(f"[green]✓ {len(unique_artist_ids)} unique artists[/green]")
    
    return all_tracks


def analyze_and_save(tracks):
    """Analyze and save track data."""
    
    console.print(f"\n{Panel('[bold yellow]📊 ANALYSIS[/bold yellow]')}")
    
    # Basic stats
    console.print("\n[bold]Overview:[/bold]")
    console.print(f"  Total tracks: {len(tracks)}")
    
    all_artists = []
    for track in tracks:
        all_artists.extend(track['artists'])
    
    console.print(f"  Unique artists: {len(set(all_artists))}")
    console.print(f"  Avg artists/track: {len(all_artists) / len(tracks):.2f}")
    
    # Year analysis
    years = []
    for track in tracks:
        date = track.get('release_date', '')
        if date and len(date) >= 4:
            try:
                years.append(int(date[:4]))
            except (ValueError, TypeError):
                pass
    
    if years:
        console.print(f"  Year range: {min(years)} - {max(years)}")
        oldies = sum(1 for y in years if y < 2000)
        console.print(f"  Pre-2000 tracks: {oldies}")
    
    # Market analysis
    south_asian_markets = {'IN', 'PK', 'BD', 'LK', 'NP'}
    tracks_in_south_asia = sum(
        1 for t in tracks 
        if any(m in south_asian_markets for m in t.get('markets', []))
    )
    console.print(f"  Available in South Asian markets: {tracks_in_south_asia}/{len(tracks)}")
    
    # Popularity analysis
    popularities = [t.get('popularity', 0) for t in tracks if t.get('popularity')]
    if popularities:
        avg_pop = sum(popularities) / len(popularities)
        console.print(f"  Avg popularity: {avg_pop:.1f}/100")
    
    # Top artists
    artist_counts = Counter(all_artists)
    console.print("\n[bold]🎤 Top 15 Artists:[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", width=3)
    table.add_column("Artist", style="cyan", width=40)
    table.add_column("Tracks", justify="right", style="green")
    
    for i, (artist, count) in enumerate(artist_counts.most_common(15), 1):
        table.add_row(str(i), artist[:40], str(count))
    
    console.print(table)
    
    # Sample tracks
    console.print("\n[bold]🎵 Sample Tracks (first 25):[/bold]")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", width=3)
    table.add_column("Track", style="cyan", width=25)
    table.add_column("Artists", style="yellow", width=25)
    table.add_column("Year", width=6)
    table.add_column("Album", style="green", width=20)
    
    for i, track in enumerate(tracks[:25], 1):
        name = track['name'][:25]
        artists = ", ".join(track['artists'])[:25]
        year = track.get('release_date', '')[:4] if track.get('release_date') else 'N/A'
        album = track.get('album', '')[:20]
        table.add_row(str(i), name, artists, year, album)
    
    console.print(table)
    
    # Save to JSON
    output_file = 'sample_100_tracks_no_genres.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tracks, f, indent=2, ensure_ascii=False)
    console.print(f"\n[green]✅ Saved to: {output_file}[/green]")
    
    # Save detailed report
    report_file = 'sample_100_tracks_analysis.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 100 + "\n")
        f.write("100 SAMPLE TRACKS - DETAILED ANALYSIS\n")
        f.write("=" * 100 + "\n\n")
        
        f.write(f"Total tracks: {len(tracks)}\n")
        f.write(f"Unique artists: {len(set(all_artists))}\n")
        f.write(f"Year range: {min(years)} - {max(years)}\n\n")
        
        f.write("=" * 100 + "\n")
        f.write("TOP 30 ARTISTS\n")
        f.write("=" * 100 + "\n")
        for i, (artist, count) in enumerate(artist_counts.most_common(30), 1):
            f.write(f"{i:3d}. {artist:60s} {count:3d} tracks\n")
        
        f.write("\n" + "=" * 100 + "\n")
        f.write("ALL TRACKS (with metadata)\n")
        f.write("=" * 100 + "\n\n")
        
        for i, track in enumerate(tracks, 1):
            f.write(f"{i}. {track['name']}\n")
            f.write(f"   Artists: {', '.join(track['artists'])}\n")
            f.write(f"   Album: {track.get('album', 'Unknown')}\n")
            f.write(f"   Year: {track.get('release_date', 'Unknown')}\n")
            f.write(f"   Popularity: {track.get('popularity', 'N/A')}/100\n")
            f.write(f"   Markets: {len(track.get('markets', []))} countries\n")
            
            # Check if available in South Asian markets
            track_markets = set(track.get('markets', []))
            sa_markets = track_markets & south_asian_markets
            if sa_markets:
                f.write(f"   South Asian markets: {', '.join(sorted(sa_markets))}\n")
            
            f.write(f"   Explicit: {'Yes' if track.get('explicit') else 'No'}\n")
            duration_min = track.get('duration_ms', 0) // 60000
            duration_sec = (track.get('duration_ms', 0) % 60000) // 1000
            f.write(f"   Duration: {duration_min}:{duration_sec:02d}\n")
            f.write("-" * 100 + "\n")
    
    console.print(f"[green]✅ Saved detailed report to: {report_file}[/green]")
    
    console.print("\n" + "=" * 80)
    console.print("[bold green]✅ Data collection complete![/bold green]")
    console.print("[dim]Note: Genre data skipped to avoid rate limits[/dim]")
    console.print("=" * 80)


if __name__ == "__main__":
    tracks = fetch_tracks_no_genres()
    if tracks:
        analyze_and_save(tracks)
