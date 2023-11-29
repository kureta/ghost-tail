# Ghost Tail
## Abstract
An RNN trained on solo piano midi files. Receives live midi input and sends back its prediction.
## Dataset features
- **interval:** In semitones.
- **delta time:** Time between last notes onset and this notes onset. This way we can easily represent arpeggios and chords.
- **duration:** Maybe in seconds, maybe in beats, or as a fraction of the duration of one measure. If in beats or measures, we may also need tempo and/or time signature.
- **velocity:** Very simple, just normalize midi velocity to \[0, 1\]
- **register:** This might be tricky. Normalize the range of the piano to \[0, 1\] and add uniform noise with a certain width (maybe half or quarter of an octave) so that the network cannot learn exact pitches, just a general register. This will be necessary since we are using intervals instead of pitches, we might go outside the register.
### Some considerations for the features
If it is not a very large number, we can just one-hot-encode intervals. However, since sizes of consecutive intervals are not completely independent, maybe we can map them to \[-1, 1\], descending and ascending intervals. But intervals are not actually continues, but discrete, so this might not be ideal.

For both duration and delta time we have many options. We can use floating point seconds, beats, or measures as our time unit. Measures makes most musical sense. Are beats or measures going to be a discrete set of fractions or floating points? If midi files have unquantized bits, are we going to quantize the? At this point floating points seem to be the easiest to implement. We might also need tempo and time signature, which would be tricky. Are we going to incorporate tempo change controls or are we going to give an *average tempo* for each track? Are we going to feed the tempo at every time step, even if it is the same tempo throughout the piece? Same applies to time signature.

Another strong aspect of using measures as the unit of time is the fact that patterns of durations and onsets would contain some information on the time signature.
