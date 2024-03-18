"""CLI for data processing."""

from pathlib import Path

import typer

from .logutils import SingletonConsole  # , get_logger
from .midi import get_piano_tracks_from_dir

DEFAULT_PATH = Path(__file__).parent.parent / "data" / "raw" / "jazz-piano-midi"

app = typer.Typer()


# TODO: maybe save all piano tracks as intermediate midi files in a directory
# TODO: convert tracks to data format (not specified yet)
# TODO: add pre-commit hooks
# TODO: add nbstripout
# TODO: make into a proper CLI
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


if __name__ == "__main__":
    app()
