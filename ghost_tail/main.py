import os
from typing import List, Union

import mido
from tqdm import tqdm

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
    if track := get_track_with_piano_in_name(tracks):
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


def main():
    # iterate through all midi files in directory
    has_piano = 0
    no_piano = 0
    corrupted = 0
    for filename in tqdm(os.listdir(RAW_MIDI_DIR)):
        if filename.endswith(".mid") or filename.endswith(".MID"):
            # print(f"Loading {filename}...")
            full_path = os.path.join(RAW_MIDI_DIR, filename)
            # load midi file using mido
            try:
                mid = mido.MidiFile(full_path)
            except ValueError:
                # print(f"Could not load {filename}.")
                corrupted += 1
                continue
            # try to get piano track
            track = get_piano_tracks(mid)
            if track:
                # print(f"{filename} has piano in {track.name}.")
                has_piano += 1
            else:
                # print(f"{filename} has no piano track.")
                no_piano += 1
    print(f"{has_piano} files have piano, {no_piano} files don't, {corrupted} files are corrupted.")


if __name__ == '__main__':
    main()
