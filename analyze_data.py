#!/usr/bin/env python3
"""
Analyze cached Spotify data to understand what we're working with.
This script reads from cache and doesn't make any API calls.
"""
import json
from collections import Counter
from cache_manager import CacheManager
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def analyze_cached_data():
    """Analyze all cached track and classification data."""
    
    cache = CacheManager()
    
    console.print(Panel("[bold cyan]🔍 ANALYZING CACHED SPOTIFY DATA[/bold cyan]"))
    
    # Get all cached tracks
    console.print("\n📊 Loading cached tracks...", style="cyan")
    
    # Read cache from JSON files
    tracks = list(cache.tracks_cache.values())
    track_count = len(tracks)
    
    console.print(f"✓ Found {track_count} cached tracks", style="green")
    
    if track_count == 0:
        console.print("\n❌ No cached data found. Run the app first to fetch tracks.", style="red")
        return
    
    # Analyze artists
    console.print("\n👥 ARTIST ANALYSIS", style="bold yellow")
    all_artists = []
    artist_track_count = Counter()
    
    for track in tracks:
        artists = track.get('artists', [])
        all_artists.extend(artists)
        for artist in artists:
            artist_track_count[artist] += 1
    
    unique_artists = set(all_artists)
    console.print(f"   Total artist references: {len(all_artists)}")
    console.print(f"   Unique artists: {len(unique_artists)}")
    console.print(f"   Average artists per track: {len(all_artists) / len(tracks):.2f}")
    
    # Top artists
    console.print("\n🎤 TOP 20 ARTISTS (by track count):", style="bold")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=4)
    table.add_column("Artist", style="cyan", width=40)
    table.add_column("Tracks", justify="right", style="green")
    
    for i, (artist, count) in enumerate(artist_track_count.most_common(20), 1):
        table.add_row(str(i), artist[:40], str(count))
    
    console.print(table)
    
    # Analyze genres
    console.print("\n🎸 GENRE ANALYSIS", style="bold yellow")
    all_genres = []
    tracks_with_genres = 0
    
    for track in tracks:
        genres = track.get('genres', [])
        if genres:
            tracks_with_genres += 1
            all_genres.extend(genres)
    
    genre_counts = Counter(all_genres)
    
    console.print(f"   Tracks with genres: {tracks_with_genres}/{len(tracks)} ({tracks_with_genres/len(tracks)*100:.1f}%)")
    console.print(f"   Total genre tags: {len(all_genres)}")
    console.print(f"   Unique genres: {len(set(all_genres))}")
    
    if genre_counts:
        console.print("\n🎵 TOP 20 GENRES:", style="bold")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("Genre", style="cyan", width=40)
        table.add_column("Count", justify="right", style="green")
        
        for i, (genre, count) in enumerate(genre_counts.most_common(20), 1):
            table.add_row(str(i), genre[:40], str(count))
        
        console.print(table)
    
    # Analyze release years
    console.print("\n📅 RELEASE YEAR ANALYSIS", style="bold yellow")
    years = []
    for track in tracks:
        date = track.get('release_date', '')
        if date and len(date) >= 4:
            try:
                year = int(date[:4])
                years.append(year)
            except (ValueError, TypeError):
                pass
    
    if years:
        years.sort()
        console.print(f"   Oldest track: {years[0]}")
        console.print(f"   Newest track: {years[-1]}")
        console.print(f"   Median year: {years[len(years)//2]}")
        
        # Decade distribution
        decade_counts = Counter((y // 10) * 10 for y in years)
        console.print("\n📊 TRACKS BY DECADE:")
        for decade in sorted(decade_counts.keys()):
            count = decade_counts[decade]
            bar = "█" * (count // 20)
            console.print(f"   {decade}s: {count:4d} {bar}")
    
    # Analyze classifications
    console.print("\n🏷️  CLASSIFICATION STATUS", style="bold yellow")
    classified_count = len(cache.classifications_cache)
    console.print(f"   Classified tracks: {classified_count}/{track_count}")
    
    if classified_count > 0:
        category_counts = Counter()
        for classification in cache.classifications_cache.values():
            category_counts[classification['category']] += 1
        
        console.print("\n📦 CLASSIFICATION DISTRIBUTION:")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Category", style="cyan", width=25)
        table.add_column("Count", justify="right", style="green")
        table.add_column("Percentage", justify="right", style="yellow")
        
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / classified_count * 100
            table.add_row(category, str(count), f"{pct:.1f}%")
        
        console.print(table)
    
    # Sample tracks
    console.print("\n🎵 SAMPLE TRACKS (first 10):", style="bold yellow")
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Track", style="cyan", width=30)
    table.add_column("Artists", style="yellow", width=30)
    table.add_column("Year", width=6)
    table.add_column("Genres", style="green", width=20)
    
    for track in tracks[:10]:
        name = track.get('name', 'Unknown')[:30]
        artists = ", ".join(track.get('artists', []))[:30]
        year = track.get('release_date', '')[:4] if track.get('release_date') else 'N/A'
        genres = ", ".join(track.get('genres', [])[:2])[:20] if track.get('genres') else 'None'
        table.add_row(name, artists, year, genres)
    
    console.print(table)
    
    # Save detailed report to file
    console.print("\n💾 Saving detailed report...", style="cyan")
    with open('data_analysis_report.txt', 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("SPOTIFY DATA ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total Tracks: {track_count}\n")
        f.write(f"Unique Artists: {len(unique_artists)}\n")
        f.write(f"Tracks with Genres: {tracks_with_genres}\n")
        f.write(f"Classified Tracks: {classified_count}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("TOP 50 ARTISTS\n")
        f.write("=" * 80 + "\n")
        for i, (artist, count) in enumerate(artist_track_count.most_common(50), 1):
            f.write(f"{i:3d}. {artist:50s} {count:4d} tracks\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("ALL GENRES (sorted by frequency)\n")
        f.write("=" * 80 + "\n")
        for genre, count in genre_counts.most_common():
            f.write(f"{count:4d}x {genre}\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("ALL TRACKS (with metadata)\n")
        f.write("=" * 80 + "\n")
        for track in tracks:
            f.write(f"\nTrack: {track.get('name')}\n")
            f.write(f"Artists: {', '.join(track.get('artists', []))}\n")
            f.write(f"Album: {track.get('album')}\n")
            f.write(f"Year: {track.get('release_date', 'N/A')}\n")
            f.write(f"Genres: {', '.join(track.get('genres', [])) or 'None'}\n")
            f.write("-" * 80 + "\n")
    
    console.print("✅ Report saved to: data_analysis_report.txt", style="green")
    
    console.print("\n" + "=" * 80, style="dim")
    console.print("✅ Analysis complete!", style="bold green")
    console.print("=" * 80, style="dim")


if __name__ == "__main__":
    analyze_cached_data()
