import os
from dataclasses import dataclass
from enum import Enum
from typing import List, Union

import mido
from tqdm.contrib.concurrent import process_map

RAW_MIDI_DIR = "../data/raw/jazz-piano-midi/"


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

    # Unfortunately there are tracks with multiple pianos. Not just 2 hands in different tracks.
    # if len(tracks) == 2:
    #     return mido.merge_tracks(tracks)

    return None


def get_piano_tracks(mid: mido.MidiFile):
    # get all tracks with note events
    tracks = [track for track in mid.tracks if track_has_note_events(track)]

    # has only one track
    if len(tracks) == 1:
        return tracks[0]

    # has piano in name
    if track := get_track_with_piano_in_name(tracks) is not None:
        return track

    # only one track has piano in program
    is_piano = []
    has_no_program = []
    for track in tracks:
        if not track_has_program_change(track):
            has_no_program.append(track)
        elif get_first_program_change_from_track(track) == 0:
            is_piano.append(track)

    # only one track has piano in program
    if len(is_piano) == 1:
        return is_piano[0]
    # only one track has no program (default is piano)
    elif len(has_no_program) == 1:
        return has_no_program[0]

    return None


class Status(Enum):
    VALID = 1
    NO_PIANO = 2
    CORRUPTED = 3


@dataclass
class Result:
    filename: str
    track: Union[mido.MidiTrack, None]
    status: Status


def process_midi_file(filename: str) -> Result:
    full_path = os.path.join(RAW_MIDI_DIR, filename)
    # load midi file using mido
    try:
        mid = mido.MidiFile(full_path)
    except ValueError:
        return Result(filename, None, Status.CORRUPTED)
    # try to get piano track
    track = get_piano_tracks(mid)
    if track is not None:
        return Result(filename, track, Status.VALID)
    else:
        return Result(filename, None, Status.NO_PIANO)


# TODO: add args for data dir
def main():
    # iterate through all midi files in directory
    files = [filename for filename in os.listdir(RAW_MIDI_DIR) if
             filename.endswith(".mid") or filename.endswith(".MID")]
    results = process_map(process_midi_file, files)
    valid_tracks = [result for result in results if result.status == Status.VALID]
    no_piano = [result for result in results if result.status == Status.NO_PIANO]
    corrupted = [result for result in results if result.status == Status.CORRUPTED]

    print(f"Found {len(valid_tracks)} piano tracks in {len(files)} files.")
    print(f"Found {len(no_piano)} files without piano.")
    print(f"Found {len(corrupted)} corrupted files.")


if __name__ == '__main__':
    main()
