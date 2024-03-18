"""CLI for data processing."""

import pickle
from dataclasses import dataclass
from pathlib import Path

import typer

from .logutils import SingletonConsole  # , get_logger
from .midi import get_piano_tracks_from_dir

DEFAULT_PATH = Path(__file__).parent.parent / "data" / "raw" / "jazz-piano-midi"

app = typer.Typer()


@dataclass
class Note:
    """Note class."""

    pitch: int
    velocity: int
    onset: float
    is_on: bool


@dataclass
class PedalState:
    """Pedal state class."""

    state: bool
    time: float


# TODO: convert tracks to data format (not specified yet)
# TODO: refactor interim preprocessing to a separate module, and parallelize
# There are 3 stages to preprocessing:
# 1. Strip all note and pedal messages from non-piano tracks in midi files and merge all tracks into one
#    That's because there might be other relevant events in other tracks (e.g. time signature, tempo, etc.)
# 2. Convert the merged track into a simpler data format (e.g. list of notes and pedal states)
# 3. Generate featires from the data format for training (e.g. offset, duration, etc.)
# 1. is done in `midi.py`, 2. is done below (to be refactored), 3. is work in progress
@app.command()
def preprocess(directory: Path = DEFAULT_PATH) -> None:
    """Main function.

    Entry point of the program.
    """
    console = SingletonConsole()
    # logger = get_logger()

    directory = Path(directory)
    console.print(f"Using {directory} as midi directory.")
    piano_tracks = get_piano_tracks_from_dir(directory)
    console.print(f"Found {len(piano_tracks)} piano tracks.")

    def is_on(msg):
        return msg.type == "note_on" and msg.velocity > 0

    for track in piano_tracks:
        pedal_events = []
        note_events = []

        for message in track.midi_data:  # type: ignore
            if message.is_cc(64):
                pedal_state = message.value >= 64
                pedal_events.append(PedalState(pedal_state, message.time))
            elif message.type in ["note_on", "note_off"]:
                if is_on(message):
                    note_events.append(Note(message.note, message.velocity, message.time, True))
                else:
                    note_events.append(Note(message.note, 0, message.time, False))

        console.print(f"Processed {track.filename.name}.")
        console.print(f"Pedal events: {len(pedal_events)}")
        console.print(f"Note events: {len(note_events)}")

        intermediate_data = {
            "pedal": pedal_events,
            "notes": note_events,
        }

        set_name = track.filename.parent.name
        save_dir = directory.parent.parent / "intermediate" / set_name
        if not save_dir.exists():
            save_dir.mkdir()
        file_path = save_dir / f"{track.filename.stem}.pkl"

        with open(file_path, "wb") as file:
            pickle.dump(intermediate_data, file)

        console.print(f"Saved intermediate data to {file_path}.")


if __name__ == "__main__":
    app()
