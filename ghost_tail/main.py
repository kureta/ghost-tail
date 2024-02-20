"""CLI for data processing."""

from pathlib import Path
from midi import get_piano_tracks_from_dir
import typer

DEFAULT_PATH = Path(__file__).parent.parent / "data" / "raw" / "jazz-piano-midi"


# TODO: maybe save all piano tracks as intermediate midi files in a directory
# TODO: convert tracks to data format (not specified yet)
# TODO: add pre-commit hooks
# TODO: add nbstripout
# TODO: make into a proper CLI
def main(directory: str = DEFAULT_PATH) -> None:
    directory = Path(directory)
    """Main function. Entry point of the program."""
    print(f"Using {directory} as midi directory.")
    get_piano_tracks_from_dir(directory)


if __name__ == "__main__":
    typer.run(main)
