"""
Main CLI interface for ForTheRekord.

Provides command-line interface using Click framework.
"""

import click
from pathlib import Path
from typing import Optional
import sys

from .config import load_config, create_default_config, get_config_path, validate_config
from .rekordbox import load_rekordbox_library
from .spotify import SpotifyClient, clean_playlist_name, clean_track_title_for_spotify
from .matching import match_rekordbox_to_spotify, boost_liked_tracks, create_match_summary


def display_progress(current: int, total: int, message: str = "") -> None:
    """Simple progress display."""
    if not message:
        message = "Progress"
    
    if total > 0:
        percent = (current / total) * 100
        print(f"\r{message}: {current}/{total} ({percent:.1f}%)", end="", flush=True)
        if current == total:
            print()  # New line when complete
    else:
        print(f"\r{message}: {current}", end="", flush=True)


def interactive_mode():
    """Placeholder for interactive mode functionality."""
    click.echo("Interactive mode is not yet implemented.")
    return False
from datetime import datetime


@click.command()
@click.option('--unmapped', 
              is_flag=True,
              help='Only process unmapped tracks')
@click.option('--remap', 
              is_flag=True, 
              help='Clear existing track mappings')
@click.option('--use-cache', 
              is_flag=True,
              help='Use cached liked tracks instead of fetching')
@click.option('--interactive', 
              is_flag=True,
              help='Enable interactive track selection')
@click.option('--verbose', '-v', 
              is_flag=True,
              help='Enable verbose output')
@click.version_option()
def main(unmapped: bool, remap: bool, use_cache: bool, 
         interactive: bool, verbose: bool) -> None:
    """
    ForTheRekord - Synchronize Rekordbox DJ library with Spotify playlists.
    
    This tool matches tracks between your Rekordbox library and Spotify,
    then synchronizes playlists between the two platforms.
    """
    
    # Load and validate configuration
    try:
        config_obj = load_config()
        if verbose:
            click.echo(f"Loaded configuration")
        
        errors = validate_config(config_obj)
        if errors:
            click.echo("Configuration errors found:", err=True)
            for error in errors:
                click.echo(f"  - {error}", err=True)
            click.echo("Please fix these errors in your configuration file.")
            sys.exit(1)
            
    except FileNotFoundError:
        click.echo("Configuration file not found.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error loading configuration: {e}", err=True)
        sys.exit(1)
    
    # Start synchronization
    start_time = datetime.now()
    
    try:
        click.echo("Starting ForTheRekord synchronization...")
        
        if verbose:
            click.echo(f"Options: unmapped={unmapped}, remap={remap}, "
                      f"use_cache={use_cache}, interactive={interactive}")
        
        # 1. Parse Rekordbox library
        click.echo("1. Parsing Rekordbox library...")
        tracks, playlists = load_rekordbox_library(config_obj.rekordbox.library_path)
        click.echo(f"   Found {len(tracks)} tracks and {len(playlists)} playlists")
        
        # 2. Initialize Spotify client
        click.echo("2. Connecting to Spotify...")
        try:
            spotify_client = SpotifyClient(config_obj)
            click.echo(f"   Connected as user: {spotify_client.user_id}")
        except Exception as e:
            click.echo(f"   Failed to connect to Spotify: {e}")
            return
        
        # 3. Get liked tracks for boosting
        click.echo("3. Loading Spotify liked tracks...")
        liked_tracks = spotify_client.get_saved_tracks()
        click.echo(f"   Found {len(liked_tracks)} liked tracks")
        
        # 4. Match tracks
        click.echo("4. Matching Rekordbox tracks to Spotify...")
        matches = match_rekordbox_to_spotify(
            tracks, 
            spotify_client, 
            threshold=config_obj.matching.similarity_threshold
        )
        
        # Boost liked tracks
        if config_obj.matching.boost_liked_tracks > 1.0:
            matches = boost_liked_tracks(matches, liked_tracks, config_obj.matching.boost_liked_tracks)
        
        # Show matching summary
        summary = create_match_summary(matches)
        click.echo(f"   Matched {summary['matched_tracks']}/{summary['total_tracks']} tracks ({summary['match_rate_percent']}%)")
        
        # 5. Sync playlists
        click.echo("5. Syncing playlists to Spotify...")
        spotify_playlists = spotify_client.get_user_playlists()
        
        for rb_playlist in playlists:
            playlist_name = rb_playlist['name']
            
            # Skip ignored playlists
            if playlist_name.lower() in [p.lower() for p in config_obj.spotify.ignore_playlists]:
                continue
            
            # Clean playlist name
            clean_name = clean_playlist_name(playlist_name, config_obj.spotify.replace_in_playlist_name)
            
            # Add prefix
            final_name = f"{config_obj.playlists.prefix}_{clean_name}" if config_obj.playlists.prefix else clean_name
            
            click.echo(f"   Processing playlist: {final_name}")
            
            # Find or create Spotify playlist
            existing_playlist = None
            for sp_playlist in spotify_playlists:
                if sp_playlist['name'] == final_name:
                    existing_playlist = sp_playlist
                    break
            
            if not existing_playlist:
                existing_playlist = spotify_client.create_playlist(final_name)
                click.echo(f"     Created new playlist")
            
            # Get tracks for this playlist
            playlist_track_ids = rb_playlist.get('track_ids', [])
            playlist_tracks = [track for track in tracks if track.get('track_id') in playlist_track_ids]
            
            # Match playlist tracks to Spotify
            playlist_matches = [match for match in matches 
                              if match['rekordbox_track'].get('track_id') in playlist_track_ids 
                              and match.get('match_found')]
            
            # Get Spotify URIs
            spotify_uris = [match['spotify_track']['spotify_uri'] 
                          for match in playlist_matches 
                          if match['spotify_track'].get('spotify_uri')]
            
            # Update playlist
            if spotify_uris:
                spotify_client.replace_playlist_tracks(existing_playlist['playlist_id'], spotify_uris)
                click.echo(f"     Updated with {len(spotify_uris)} tracks")
            else:
                click.echo(f"     No matching tracks found")
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        click.echo(f"\nSync completed in {duration:.2f} seconds")
        
    except KeyboardInterrupt:
        click.echo("\nSynchronization cancelled by user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error during synchronization: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
