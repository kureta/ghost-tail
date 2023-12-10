from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Union

import loguru
import mido
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.progress import Progress
from systemd.journal import JournalHandler


def _get_record_color(record: loguru.Record) -> str:
    """Get color for log message"""
    color_map = {
        "TRACE": "dim blue",
        "DEBUG": "cyan",
        "INFO": "bold",
        "SUCCESS": "bold green",
        "WARNING": "yellow",
        "ERROR": "bold red",
        "CRITICAL": "bold white on red",
    }
    return color_map.get(record["level"].name, "cyan")


def _log_formatter(record: loguru.Record) -> str:
    """Log message formatter"""
    color = _get_record_color(record)
    return (
        f"[not bold green]{record['time']:YYYY/MM/DD HH:mm:ss}[/not bold green] | "
        + f"{record['level'].icon} - [{color}]{{message}}[/{color}]"
    )


def _journald_formatter(record: loguru.Record) -> str:
    """Log message formatter for journald"""
    return f"{record['level'].name}: {record['message']}"


console = Console(color_system="truecolor", stderr=True)


def track_has_note_events(track: mido.MidiTrack) -> bool:
    return any(message.type == "note_on" for message in track)


def track_has_program_change(track: mido.MidiTrack) -> bool:
    return any(message.type == "program_change" for message in track)


def get_first_program_change_from_track(track: mido.MidiTrack) -> Union[mido.Message, None]:
    for message in track:
        if message.type == "program_change":
            return message.program

    return None


def get_track_with_piano_in_name(mid: List[mido.MidiTrack]) -> Union[mido.MidiTrack, None]:
    tracks = [track for track in mid if "piano" in track.name.strip().lower()]

    if len(tracks) == 1:
        return tracks[0]

    # unfortunately there are tracks with multiple pianos. Not just 2 hands in different tracks.
    # if len(tracks) == 2:
    #     return mido.merge_tracks(tracks)

    return None


def get_piano_track_from_mid(mid: mido.MidiFile) -> Union[mido.MidiTrack, None]:
    # get all tracks with note events
    tracks = [track for track in mid.tracks if track_has_note_events(track)]

    # has only one track
    if len(tracks) == 1:
        logger.trace("Found only one track with note events. Assuming it is the piano track.")
        return tracks[0]

    # has piano in name
    if (track := get_track_with_piano_in_name(tracks)) is not None:
        logger.trace("Found unique track with piano in name.")
        return track

    # scan program change messages
    is_piano = []
    has_no_program = []
    for track in tracks:
        if not track_has_program_change(track):
            has_no_program.append(track)
        elif get_first_program_change_from_track(track) == 0:
            is_piano.append(track)

    # only one track has piano in program
    if len(is_piano) == 1:
        logger.trace("Found unique track with piano in program.")
        return is_piano[0]

    # only one track has no program (default is piano)
    elif len(has_no_program) == 1:
        logger.trace(
            "Found unique track with no program change. \
            Assuming it is the piano track since default instrument is piano."
        )
        return has_no_program[0]

    return None


class Status(Enum):
    VALID = 1
    NO_PIANO = 2
    CORRUPTED = 3


@dataclass
class Result:
    filename: Path
    track: mido.MidiTrack
    status: Status


def get_piano_track_from_file(full_path: Path) -> Result:
    filename = full_path.name
    # load midi file using mido
    try:
        mid = mido.MidiFile(full_path)
    except ValueError:
        logger.trace(f"Could not load {filename}.")
        return Result(full_path, mido.MidiTrack(), Status.CORRUPTED)
    # try to get piano track
    track = get_piano_track_from_mid(mid)
    if track is not None:
        return Result(full_path, track, Status.VALID)
    else:
        logger.trace(f"Could not find piano track in {filename}.")
        return Result(full_path, mido.MidiTrack(), Status.NO_PIANO)


def get_piano_tracks_from_dir(midi_dir: Path) -> List[mido.MidiTrack]:
    # iterate through all midi files in directory
    files = list(midi_dir.glob("*.mid")) + list(midi_dir.glob("*.MID"))
    logger.info(f"Found {len(files)} midi files in {midi_dir}. Processing...")

    # parallel process all files
    results = []
    with Progress(console=console, auto_refresh=False) as progress:
        task = progress.add_task("Processing...", total=len(files))
        with ProcessPoolExecutor(max_workers=12) as executor:
            for f in files:
                results.append(executor.submit(get_piano_track_from_file, f))
            while (n_done := sum(result.done() for result in results)) < len(files):
                progress.update(task, completed=n_done)
                progress.refresh()

    results = [result.result() for result in results]

    # filter results
    valid_tracks = [result for result in results if result.status == Status.VALID]
    logger.info(f"Found {len(valid_tracks)} piano tracks in {len(files)} files.")

    no_piano = [result for result in results if result.status == Status.NO_PIANO]
    logger.info(f"Found {len(no_piano)} files without piano.")

    corrupted = [result for result in results if result.status == Status.CORRUPTED]
    logger.info(f"Found {len(corrupted)} corrupted files.")

    return [result.track for result in valid_tracks]


# TODO: maybe save all piano tracks as intermediate midi files in a directory
# TODO: convert tracks to data format (not specified yet)
# TODO: add pre-commit hooks
# TODO: add nbstripout
def main(args):
    if len(args) > 1:
        print("Usage: python main.py <path to midi directory>")
        exit(1)
    elif len(args) == 0:
        print("No midi directory specified. Using default directory.")
        my_path = Path(__file__).parent.parent
        midi_dir = my_path / "data" / "raw" / "jazz-piano-midi"
        get_piano_tracks_from_dir(midi_dir)
    else:
        midi_dir = Path(args[0])
        print(f"Using {midi_dir} as midi directory.")
        get_piano_tracks_from_dir(midi_dir)


if __name__ == "__main__":
    import sys

    load_dotenv()
    log_level = os.getenv("LOG_LEVEL", "INFO")

    logger.remove()
    logger.add(
        console.print,
        level=log_level,
        format=_log_formatter,
        colorize=True,
    )
    logger.add(
        JournalHandler(SYSLOG_IDENTIFIER="Ghost Tail"),
        level=log_level,
        format=_journald_formatter,
        colorize=False,
    )

    main(sys.argv[1:])
