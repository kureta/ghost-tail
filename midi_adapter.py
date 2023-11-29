import glob
import logging
import os
from functools import partial
from random import randrange

import mido
import numpy as np

from tools import *


class NoteEvent:
    def __init__(self, pitch, velocity, time, duration):
        self.pitch = pitch
        self.velocity = velocity
        self.time = time
        self.duration = duration

    def __repr__(self):
        return "pitch: {}, velocity: {}, time: {}, duration: {}".format(
            self.pitch, self.velocity, self.time, self.duration
        )


# default tempo is 500000 microseconds per quarter note = 120 beats per minute
DEFAULT_TEMPO = 500000
# default resolution is 480 ticks per quarter note
DEFAULT_RESOLUTION = 480
# Default time signature is 4/4 the other two numbers are
# Internal MIDI metronome clock ticks 24 times per quarter note as per MIDI specification
# 24 means the metronome should tick every quarter notes
# 8 is the number of 32nd notes per one quarter note
DEFAULT_TIME_SIGNATURE = (4, 4, 24, 8)

DEFAULT_BAR_LENGTH = int(
    (DEFAULT_RESOLUTION * 4) * (DEFAULT_TIME_SIGNATURE[0] / DEFAULT_TIME_SIGNATURE[1])
)

logger = logging.getLogger(__name__)


def get_time_signature(track):
    time_signature_changes = list(filter(lambda x: x.type == "time_signature", track))
    if len(time_signature_changes) == 1:
        time_sig = (
            time_signature_changes[0].numerator,
            time_signature_changes[0].denominator,
            time_signature_changes[0].clocks_per_click,
            time_signature_changes[0].notated_32nd_notes_per_beat,
        )

    elif len(time_signature_changes) == 0:
        time_sig = DEFAULT_TIME_SIGNATURE
    else:
        logger.warning("\t\tThe track has multiple time signature events!!!")
        # TODO: handle time signature changes URGENT!!!
        time_sig = (
            time_signature_changes[0].numerator,
            time_signature_changes[0].denominator,
            time_signature_changes[0].clocks_per_click,
            time_signature_changes[0].notated_32nd_notes_per_beat,
        )
    return time_sig


def get_bar_length(time_sig, ticks_per_beat):
    return int((ticks_per_beat * 4) * (time_sig[0] / time_sig[1]))


def ticks_to_bars(track, bar_len):
    def t_to_b(note):
        return assoc(note, "time", note.time / bar_len)

    return list(map(t_to_b, track))


def bars_to_ticks(track, bar_len):
    def b_to_t(note):
        return assoc(note, "time", int(note.time * bar_len))

    return list(map(b_to_t, track))


def filter_out_notes(track):
    return list(filter(lambda x: x.type == "note_on" or x.type == "note_off", track))


def notes_with_durations(vals):
    def ons_and_offs(val):
        # here we sort events on notes so we can couple on and off events of the same note below
        def split(a, x):
            if x.velocity > 0 and x.type == "note_on":
                return a[0] + [x], a[1]
            elif x.velocity == 0 or x.type == "note_off":
                return a[0], a[1] + [x]
            else:
                return a

        ons, offs = reduce(split, val, ([], []))
        ons.sort(key=lambda x: (x.note, x.time))
        offs.sort(key=lambda x: (x.note, x.time))
        return ons, offs

    def note_dur(on, off):
        result = assoc(on, "duration", off.time - on.time)
        return result

    notes = list(map(note_dur, *ons_and_offs(vals)))
    return sorted(notes, key=lambda x: (x.time, x.note))


def format_notes(notes):
    # format the results of all previous calculations into a named tuple
    def format_one_note(note):
        note = NoteEvent(
            pitch=note.note,
            velocity=note.velocity,
            time=note.time,
            duration=note.duration,
        )  # Fraction(note.duration).limit_denominator(64))
        return note

    result = map(format_one_note, notes)
    return list(result)


def filter_tempos(track):
    return list(filter(lambda x: x.type == "set_tempo", track))


def first_tempo(track):
    tempos = filter_tempos(track)

    try:
        return next(tempos).tempo
    except StopIteration:
        return DEFAULT_TEMPO


def merge_tracks_absolute(tracks):
    midi_in = []
    for t in tracks:
        midi_in += do_on_key(delta_to_absolute, "time")(t)
    midi_in = sorted(midi_in, key=lambda x: x.time)
    # midi_in = do_on_key(absolute_to_delta, 'time')(midi_in)
    return midi_in


def midi_to_note_events(path):
    midi_file = mido.MidiFile(path)
    first_track = midi_file.tracks[0]

    time_signature = get_time_signature(first_track)
    bar_length = get_bar_length(time_signature, midi_file.ticks_per_beat)

    merged_tracks = merge_tracks_absolute(midi_file.tracks)

    notes = compose(
        format_notes,
        do_on_key(absolute_to_delta, "time"),
        notes_with_durations,
        filter_out_notes,
        partial(ticks_to_bars, bar_len=bar_length),
    )(merged_tracks)

    return notes


def note_events_to_midi(notes, path):
    midi_track = mido.MidiTrack()

    notes = do_on_key(delta_to_absolute, "time")(notes)

    for note in notes:
        midi_track.append(
            mido.Message(
                "note_on", note=note.pitch, velocity=note.velocity, time=note.time
            )
        )
        midi_track.append(
            mido.Message(
                "note_off",
                note=note.pitch,
                velocity=note.velocity,
                time=note.duration + note.time,
            )
        )

    midi_track = sorted(midi_track, key=lambda x: x.time)
    midi_track = do_on_key(absolute_to_delta, "time")(midi_track)
    midi_track = bars_to_ticks(midi_track, DEFAULT_BAR_LENGTH)

    with mido.MidiFile() as mid:
        mid.ticks_per_beat = DEFAULT_RESOLUTION
        midi_track.append(
            mido.MetaMessage(
                "time_signature",
                numerator=DEFAULT_TIME_SIGNATURE[0],
                denominator=DEFAULT_TIME_SIGNATURE[1],
                clocks_per_click=DEFAULT_TIME_SIGNATURE[2],
                notated_32nd_notes_per_beat=DEFAULT_TIME_SIGNATURE[3],
                time=0,
            )
        )
        midi_track.append(mido.MetaMessage("set_tempo", tempo=DEFAULT_TEMPO, time=0))

        mid.tracks.append(midi_track)

        mid.save(path)


def load_midi_dir(dataset_dir):
    file_names1 = os.path.join(dataset_dir, "*.mid")
    file_names2 = os.path.join(dataset_dir, "*.MID")
    file_full_paths1 = glob.glob(file_names1)
    file_full_paths2 = glob.glob(file_names2)
    file_full_paths = file_full_paths1 + file_full_paths2

    print("Creating training data files")
    notes = list(map(midi_to_note_events, file_full_paths))

    return notes


# Above = midi => intermedite, below = intermediate => data


def note_events_to_matrix(notes):
    return [[note.pitch, note.velocity, note.time, note.duration] for note in notes]


def matrix_to_note_events(data):
    return [
        NoteEvent(
            pitch=int(note[0]), velocity=int(note[1]), time=note[2], duration=note[3]
        )
        for note in data
    ]


def from_midi_folder_to_note_events(folder_path):
    data = load_midi_dir(folder_path)
    data = list(map(note_events_to_matrix, data))
    return data


def split_into_subseqs(data, maxlen, step):
    # cut the text in semi-redundant sequences of maxlen characters
    # on list of note events (single midi)
    subseqs = []
    next_chars = []
    for i in range(0, len(data) - maxlen, step):
        subseqs.append(data[i : i + maxlen])
        next_chars.append(data[i + 1 : i + maxlen + 1])
    return subseqs, next_chars


def note_events_to_subseqs(data_set, maxlen=40, step=1):
    # on list of list of note events (multiple midis)
    subseqs = []
    next_chars = []
    for data_point in data_set:
        a, b = split_into_subseqs(data_point, maxlen, step)
        subseqs.append(a)
        next_chars.append(b)

    subseqs = np.concatenate(subseqs)
    next_chars = np.concatenate(next_chars)

    return subseqs, next_chars


def normalize(data):
    normalizer = np.apply_along_axis(max, 0, data)
    normalizer = np.apply_along_axis(max, 0, normalizer)
    normalized = data / normalizer
    return normalized, normalizer


def midi_to_nn_input(midi_path, data_path, target_path, ratios_path):
    note_events = from_midi_folder_to_note_events(midi_path)
    sub_seqs, next_chars = note_events_to_subseqs(note_events, 25, 1)

    X, ratios = normalize(sub_seqs)
    y = next_chars / ratios
    write_pickle(data_path, X)
    write_pickle(target_path, y)
    write_pickle(ratios_path, ratios)


def matrix_to_midi(X, ratios):
    unscaled = matrix_to_note_events(X * ratios)
    note_events_to_midi(unscaled, "out/out.mid")


def generate_midi(source, model, ratios):
    index = randrange(source.shape[0])
    seed = source[index]

    generated = np.copy(seed)

    x_ = np.zeros([1, seed.shape[0], 4])

    for i in range(1024):
        x_[0] = seed
        next_char = model.predict(x_, verbose=0)[0]
        generated = np.concatenate((generated, [next_char[-1]]))
        seed = np.concatenate((seed[1:], [next_char[-1]]))

    matrix_to_midi(generated, ratios)


if __name__ == "__main__":
    midi_to_nn_input(
        "../raw_data/chopin/",
        "../data/chopin-25-1.pkl",
        "../data/chopin-25-1-y.pkl",
        "../data/chopin-25-1-ratios.pkl",
    )
