#!/usr/bin/env python3
"""
Recover track data from temporary cache files.
"""
import json
import os
import glob
from rich.console import Console
from collections import Counter

console = Console()

def recover_cache_data():
    """Recover data from .tmp files in .cache directory."""
    
    console.print("[bold cyan]🔍 Recovering data from cache tmp files...[/bold cyan]")
    
    # Find all tmp files
    tmp_files = glob.glob('.cache/*.tmp')
    console.print(f"Found {len(tmp_files)} temporary files")
    
    if not tmp_files:
        console.print("[red]No temporary files found[/red]")
        return
    
    # Sort by size to get the largest ones (most likely to have full data)
    tmp_files_with_size = [(f, os.path.getsize(f)) for f in tmp_files]
    tmp_files_with_size.sort(key=lambda x: x[1], reverse=True)
    
    console.print(f"\nLargest temporary files:")
    for f, size in tmp_files_with_size[:10]:
        console.print(f"  {f}: {size/1024:.1f} KB")
    
    # Try to load the largest valid JSON file
    all_tracks = {}
    valid_files = 0
    
    console.print(f"\n[cyan]Attempting to parse tmp files...[/cyan]")
    for filepath, size in tmp_files_with_size:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict) and data:
                    # Check if it looks like track data
                    sample_key = next(iter(data))
                    sample_value = data[sample_key]
                    
                    if isinstance(sample_value, dict) and 'name' in sample_value:
                        # This looks like track metadata
                        console.print(f"  ✓ {os.path.basename(filepath)}: {len(data)} tracks")
                        all_tracks.update(data)
                        valid_files += 1
        except (json.JSONDecodeError, IOError, StopIteration) as e:
            # Silently skip invalid files
            pass
    
    console.print(f"\n[green]✓ Recovered {len(all_tracks)} tracks from {valid_files} files[/green]")
    
    if not all_tracks:
        console.print("[red]Could not recover any valid track data[/red]")
        return
    
    # Analyze recovered data
    console.print("\n[bold yellow]📊 RECOVERED DATA ANALYSIS[/bold yellow]")
    
    # Count artists
    all_artists = []
    artist_counts = Counter()
    for track in all_tracks.values():
        artists = track.get('artists', [])
        all_artists.extend(artists)
        for artist in artists:
            artist_counts[artist] += 1
    
    console.print(f"  Total tracks: {len(all_tracks)}")
    console.print(f"  Unique artists: {len(set(all_artists))}")
    
    # Count genres
    tracks_with_genres = sum(1 for t in all_tracks.values() if t.get('genres'))
    console.print(f"  Tracks with genres: {tracks_with_genres}/{len(all_tracks)}")
    
    # Sample tracks
    console.print("\n[bold]Sample tracks:[/bold]")
    for i, (track_id, track) in enumerate(list(all_tracks.items())[:10], 1):
        name = track.get('name', 'Unknown')
        artists = ', '.join(track.get('artists', []))
        console.print(f"  {i}. {name} - {artists}")
    
    # Save to file
    output_file = 'recovered_tracks.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_tracks, f, indent=2, ensure_ascii=False)
    
    console.print(f"\n[green]✅ Saved recovered data to: {output_file}[/green]")
    
    # Also create a detailed text report
    report_file = 'recovered_tracks_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write("RECOVERED TRACKS REPORT\n")
        f.write("=" * 80 + "\n\n")
        
        f.write(f"Total tracks recovered: {len(all_tracks)}\n")
        f.write(f"Unique artists: {len(set(all_artists))}\n")
        f.write(f"Tracks with genres: {tracks_with_genres}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("TOP 50 ARTISTS\n")
        f.write("=" * 80 + "\n")
        for i, (artist, count) in enumerate(artist_counts.most_common(50), 1):
            f.write(f"{i:3d}. {artist:50s} {count:4d} tracks\n")
        
        f.write("\n" + "=" * 80 + "\n")
        f.write("ALL TRACKS\n")
        f.write("=" * 80 + "\n")
        for track in all_tracks.values():
            f.write(f"\nTrack: {track.get('name')}\n")
            f.write(f"Artists: {', '.join(track.get('artists', []))}\n")
            f.write(f"Album: {track.get('album')}\n")
            f.write(f"Year: {track.get('release_date', 'N/A')}\n")
            f.write(f"Genres: {', '.join(track.get('genres', [])) or 'None'}\n")
            f.write("-" * 80 + "\n")
    
    console.print(f"[green]✅ Saved detailed report to: {report_file}[/green]")

if __name__ == "__main__":
    recover_cache_data()
