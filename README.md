## Abstract

An RNN trained on solo piano midi files. Receives live midi input and sends back its prediction.

## Dataset features

- **interval:** In semitones. Interval of initial note is zero.
- **delta time:** Time between last notes onset and this notes onset. This way we can easily represent arpeggios and chords.
- **duration:** Maybe in seconds, maybe in beats, or as a fraction of the duration of one measure. If in beats or measures, we may also need tempo and/or time signature.
- **velocity:** Very simple, just normalize midi velocity to \[0, 1\]
- **register:** This might be tricky. Normalize the range of the piano to \[0, 1\] and add uniform noise with a certain width (maybe half or quarter of an octave) so that the network cannot learn exact pitches, just a general register. This will be necessary since we are using intervals instead of pitches, we might go outside the register.

### Some considerations for the features

If it is not a very large number, we can just one-hot-encode intervals.
However, since sizes of consecutive intervals are not completely independent, maybe we can map them to \[-1, 1\], descending and ascending intervals.
But intervals are not actually continuous, but discrete, so this might not be ideal.

For both duration and delta time we have many options.
We can use floating point seconds, beats, or measures as our time unit.
Measures make most musical sense.
Are beats or measures going to be a discrete set of fractions or floating points? If midi files have unquantized bits, are we going to quantize them? At this point floating points seem to be the easiest to implement.
We might also need tempo and time signature, which would be tricky.
Are we going to incorporate tempo change messages or are we going to give an _average tempo_ for each track? Are we going to feed the tempo at every time step, even if it is the same tempo throughout the piece? Same applies to time signature.

Another strong aspect of using measures as the unit of time is the fact that patterns of durations and onsets would contain some information on the time signature.

## Interaction

It will not know `duration` until the player releases a key.
It has to at least wait for that.
We may also want to "prime" it with more than one note.
Also, is it going to respond to each note with a note? Probably not.
Also, we need to have a buffer and keep time in order to store generated notes and play them after `delta` amount of time passes.

So we need to carefully consider when to feed which notes (player's or RNN's previous note) and when to get generated notes.

## PROBLEM!

If we use measures as our unit of time, live input has to have a fixed tempo and time signature.
