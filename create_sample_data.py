#!/usr/bin/env python3
"""
Create sample track data to show what we'll be working with.
This creates a smaller test dataset similar to your real data.
"""
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def create_sample_tracks():
    """Create sample tracks representing different genres/languages."""
    
    sample_tracks = {
        # English Pop
        "track_001": {
            "id": "track_001",
            "name": "Anti-Hero",
            "artists": ["Taylor Swift"],
            "album": "Midnights",
            "release_date": "2022-10-21",
            "genres": ["pop", "singer-songwriter"],
            "markets": ["US", "GB", "CA", "AU"]
        },
        "track_002": {
            "id": "track_002",
            "name": "Flowers",
            "artists": ["Miley Cyrus"],
            "album": "Endless Summer Vacation",
            "release_date": "2023-01-13",
            "genres": ["pop", "dance pop"],
            "markets": ["US", "GB", "CA", "AU"]
        },
        
        # Hindi Bollywood
        "track_003": {
            "id": "track_003",
            "name": "Kesariya",
            "artists": ["Arijit Singh", "Pritam"],
            "album": "Brahmastra",
            "release_date": "2022-07-17",
            "genres": ["filmi", "bollywood", "indian pop"],
            "markets": ["IN", "GB", "US"]
        },
        "track_004": {
            "id": "track_004",
            "name": "Chaleya",
            "artists": ["Arijit Singh", "Anirudh Ravichander"],
            "album": "Jawan",
            "release_date": "2023-08-14",
            "genres": ["filmi", "bollywood"],
            "markets": ["IN", "GB", "US"]
        },
        
        # Punjabi
        "track_005": {
            "id": "track_005",
            "name": "GOAT",
            "artists": ["Diljit Dosanjh"],
            "album": "GOAT",
            "release_date": "2020-07-30",
            "genres": ["punjabi pop", "bhangra"],
            "markets": ["IN", "CA", "GB"]
        },
        "track_006": {
            "id": "track_006",
            "name": "295",
            "artists": ["Sidhu Moose Wala"],
            "album": "No Name",
            "release_date": "2019-08-08",
            "genres": ["punjabi hip hop", "desi hip hop"],
            "markets": ["IN", "CA", "GB"]
        },
        
        # Phonk/Instrumental
        "track_007": {
            "id": "track_007",
            "name": "MONTAGEM - PR FUNK",
            "artists": ["Bibi Babydoll", "DJ Anderson do Paraiso"],
            "album": "Single",
            "release_date": "2023-05-12",
            "genres": ["brazilian phonk", "funk carioca"],
            "markets": ["BR", "US", "GB"]
        },
        "track_008": {
            "id": "track_008",
            "name": "Murder In My Mind",
            "artists": ["Kordhell"],
            "album": "Single",
            "release_date": "2022-09-07",
            "genres": ["phonk", "drift phonk"],
            "markets": ["US", "GB", "CA"]
        },
        
        # Oldies (pre-2000)
        "track_009": {
            "id": "track_009",
            "name": "Bohemian Rhapsody",
            "artists": ["Queen"],
            "album": "A Night at the Opera",
            "release_date": "1975-10-31",
            "genres": ["classic rock", "progressive rock"],
            "markets": ["US", "GB", "CA", "AU"]
        },
        "track_010": {
            "id": "track_010",
            "name": "Hotel California",
            "artists": ["Eagles"],
            "album": "Hotel California",
            "release_date": "1976-12-08",
            "genres": ["classic rock", "soft rock"],
            "markets": ["US", "GB", "CA", "AU"]
        },
        
        # Hip Hop/Rap
        "track_011": {
            "id": "track_011",
            "name": "Rich Flex",
            "artists": ["Drake", "21 Savage"],
            "album": "Her Loss",
            "release_date": "2022-11-04",
            "genres": ["hip hop", "trap"],
            "markets": ["US", "GB", "CA", "AU"]
        },
        "track_012": {
            "id": "track_012",
            "name": "FE!N",
            "artists": ["Travis Scott", "Playboi Carti"],
            "album": "UTOPIA",
            "release_date": "2023-07-28",
            "genres": ["hip hop", "trap", "rage"],
            "markets": ["US", "GB", "CA"]
        },
        
        # EDM/Electronic
        "track_013": {
            "id": "track_013",
            "name": "I'm Good (Blue)",
            "artists": ["David Guetta", "Bebe Rexha"],
            "album": "Single",
            "release_date": "2022-08-26",
            "genres": ["edm", "dance pop", "electro house"],
            "markets": ["US", "GB", "CA", "AU"]
        },
        
        # Indie/Alternative
        "track_014": {
            "id": "track_014",
            "name": "Heat Waves",
            "artists": ["Glass Animals"],
            "album": "Dreamland",
            "release_date": "2020-06-29",
            "genres": ["indie rock", "alternative"],
            "markets": ["US", "GB", "CA", "AU"]
        },
        
        # Mixed language (collaboration)
        "track_015": {
            "id": "track_015",
            "name": "Vaste",
            "artists": ["Dhvani Bhanushali", "Tanishk Bagchi"],
            "album": "Single",
            "release_date": "2019-03-01",
            "genres": ["indian pop", "indi-pop"],
            "markets": ["IN", "GB", "US"]
        },
    }
    
    return sample_tracks


def analyze_sample_data():
    """Analyze and display sample track data."""
    
    tracks = create_sample_tracks()
    
    console.print(Panel("[bold cyan]🎵 SAMPLE TRACK DATA ANALYSIS[/bold cyan]"))
    console.print(f"\n[green]Created {len(tracks)} sample tracks[/green]")
    
    # Display all tracks in a table
    console.print("\n[bold yellow]📊 SAMPLE TRACKS:[/bold yellow]")
    table = Table(show_header=True, header_style="bold magenta", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Track", style="cyan", width=25)
    table.add_column("Artists", style="yellow", width=25)
    table.add_column("Year", width=6)
    table.add_column("Genres", style="green", width=20)
    table.add_column("Expected Category", style="blue", width=15)
    
    # Map tracks to expected categories
    category_mapping = {
        "track_001": "English",
        "track_002": "English",
        "track_003": "Hindi",
        "track_004": "Hindi",
        "track_005": "Punjabi",
        "track_006": "Punjabi",
        "track_007": "Phonk/Instrumental",
        "track_008": "Phonk/Instrumental",
        "track_009": "Oldies",
        "track_010": "Oldies",
        "track_011": "English",
        "track_012": "English",
        "track_013": "English",
        "track_014": "English",
        "track_015": "Hindi",
    }
    
    for i, (track_id, track) in enumerate(tracks.items(), 1):
        name = track['name'][:25]
        artists = ", ".join(track['artists'])[:25]
        year = track['release_date'][:4]
        genres = ", ".join(track['genres'][:2])[:20]
        expected = category_mapping[track_id]
        
        table.add_row(str(i), name, artists, year, genres, expected)
    
    console.print(table)
    
    # Show what the LLM will see for classification
    console.print("\n[bold yellow]🤖 SAMPLE LLM PROMPTS:[/bold yellow]")
    
    sample_tracks_for_prompt = [
        tracks["track_003"],  # Hindi
        tracks["track_005"],  # Punjabi
        tracks["track_008"],  # Phonk
    ]
    
    for track in sample_tracks_for_prompt:
        console.print(f"\n[bold]Track: {track['name']}[/bold]")
        console.print(f"  Artists: {', '.join(track['artists'])}")
        console.print(f"  Album: {track['album']}")
        console.print(f"  Year: {track['release_date'][:4]}")
        console.print(f"  Genres: {', '.join(track['genres'])}")
        console.print(f"  Markets: {', '.join(track['markets'])}")
        
        # Show what language detection might find
        from langdetect import detect
        try:
            detected_lang = detect(track['name'])
            console.print(f"  [dim]Detected language: {detected_lang}[/dim]")
        except:
            console.print(f"  [dim]Language detection failed[/dim]")
    
    # Save to file
    output_file = 'sample_tracks.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tracks, f, indent=2, ensure_ascii=False)
    
    console.print(f"\n[green]✅ Sample data saved to: {output_file}[/green]")
    
    # Show statistics
    console.print("\n[bold yellow]📈 STATISTICS:[/bold yellow]")
    from collections import Counter
    
    all_genres = []
    all_artists = []
    years = []
    
    for track in tracks.values():
        all_genres.extend(track['genres'])
        all_artists.extend(track['artists'])
        years.append(int(track['release_date'][:4]))
    
    console.print(f"  Unique artists: {len(set(all_artists))}")
    console.print(f"  Unique genres: {len(set(all_genres))}")
    console.print(f"  Year range: {min(years)} - {max(years)}")
    
    genre_counts = Counter(all_genres)
    console.print(f"\n  Top 5 genres:")
    for genre, count in genre_counts.most_common(5):
        console.print(f"    - {genre}: {count}")
    
    console.print("\n[bold green]✅ This represents the type of data your full collection will have![/bold green]")
    console.print("[dim]Your actual data has 2556 tracks with 2083 unique artists.[/dim]")


if __name__ == "__main__":
    analyze_sample_data()
