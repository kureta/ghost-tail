"""Loads midi files from a directory and extracts piano tracks from them."""
# TODO: not enough heuristics to find piano tracks.
# TODO: retrieve tempo. Might be changing over time (alo time signature)

from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from time import sleep
from typing import List, Union

import mido
from rich.progress import Progress

from logutils import get_console, get_logger

logger = get_logger()
console = get_console()


def track_has_note_events(track: mido.MidiTrack) -> bool:
    """Some tracks have no note events. We need to filter them out."""
    return any(message.type == "note_on" for message in track)


def track_has_program_change(track: mido.MidiTrack) -> bool:
    """Program change messages are used to change the instrument.
    If a track has no program change, it is assumed to be a piano track.
    """
    return any(message.type == "program_change" for message in track)


def get_first_program_change_from_track(track: mido.MidiTrack) -> Union[mido.Message, None]:
    """Get the first program change message from a track. This is used to determine the instrument.
    Currently, we only look at the first program change message.
    """
    for message in track:
        if message.type == "program_change":
            return message.program

    return None


# TODO: handle multiple tracks with piano in name, they are probably 2 hands of the same piano.
def get_track_with_piano_in_name(mid: List[mido.MidiTrack]) -> Union[int, None]:
    """See if there is a track with piano in its name. If there is only one, return it."""
    tracks = [track for track in mid if "piano" in track.name.strip().lower()]

    if len(tracks) == 1:
        return 0

    # unfortunately there are tracks with multiple pianos. Not just 2 hands in different tracks.
    # if len(tracks) == 2:
    #     return mido.merge_tracks(tracks)

    return None


def get_piano_track_from_mid(mid: mido.MidiFile) -> Union[int, None]:
    """Apply a series of heuristics to find the piano track in a midi file."""
    # get all tracks with note events
    tracks = [track for track in mid.tracks if track_has_note_events(track)]

    # has only one track
    if len(tracks) == 1:
        return 0

    # has piano in name
    if (track_idx := get_track_with_piano_in_name(tracks)) is not None:
        return track_idx

    # scan program change messages
    is_piano = []
    has_no_program = []
    for idx, track in enumerate(tracks):
        if not track_has_program_change(track):
            has_no_program.append(idx)
        elif get_first_program_change_from_track(track) == 0:
            is_piano.append(idx)

    # only one track has piano in program
    if len(is_piano) == 1:
        return is_piano[0]

    # only one track has no program (default is piano)
    elif len(has_no_program) == 1:
        return has_no_program[0]

    return None


class Status(Enum):
    """Status of midi file processing."""
    VALID = 1
    NO_PIANO = 2
    CORRUPTED = 3


@dataclass
class Result:
    """Result of processing a midi file."""
    filename: Path
    track_idx: Union[int, None]
    midi: Union[mido.MidiFile, None]
    status: Status


def get_piano_track_from_file(full_path: Path) -> Result:
    """Load a midi file and extract the piano track from it."""
    filename = full_path.name
    # load midi file using mido
    try:
        mid = mido.MidiFile(full_path)
    except ValueError:
        logger.warning(f"Could not load {filename}.")
        return Result(full_path, None, None, Status.CORRUPTED)
    # try to get piano track
    track = get_piano_track_from_mid(mid)
    if track is not None:
        logger.info(f"Found piano track in {filename}.")
        return Result(full_path, track, mid, Status.VALID)
    else:
        logger.warning(f"Could not find piano track in {filename}.")
        return Result(full_path, None, None, Status.NO_PIANO)


def get_piano_tracks_from_dir(midi_dir: Path) -> List[Result]:
    """Load all midi files from a directory and extract the piano tracks from them."""
    # iterate through all midi files in directory
    files = list(midi_dir.glob("*.mid")) + list(midi_dir.glob("*.MID"))
    logger.info(f"Found {len(files)} midi files in {midi_dir}. Processing...")

    # parallel process all files
    with Progress(console=console, auto_refresh=False) as progress:
        task = progress.add_task("Processing...", total=len(files))
        with ProcessPoolExecutor() as executor:
            results = [executor.submit(get_piano_track_from_file, f) for f in files]
            while (n_done := sum(result.done() for result in results)) < len(files):
                progress.update(task, completed=n_done)
                progress.refresh()
                sleep(0.1)
            progress.update(task, completed=len(files))
            progress.refresh()

    results = [result.result() for result in results]

    # filter results
    valid_tracks = [result for result in results if result.status == Status.VALID]
    logger.info(f"Found {len(valid_tracks)} piano tracks in {len(files)} files.")

    no_piano = [result for result in results if result.status == Status.NO_PIANO]
    logger.info(f"Found {len(no_piano)} files without piano.")

    corrupted = [result for result in results if result.status == Status.CORRUPTED]
    logger.info(f"Found {len(corrupted)} corrupted files.")

    return valid_tracks
