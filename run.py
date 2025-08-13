import mido
import pygame
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import numpy as np

# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# --- Constants ---
SOUNDS_DIR = Path("sounds")

# --- Enums and Config ---
class PitchShiftFill(Enum):
    OFF = 0
    FORWARD = 1
    BACKWARD = 2

@dataclass
class MidiSoundConfig:
    note_map: dict                   # {note_number: Path("path/to/file")}
    pitch_shift_fill: PitchShiftFill = PitchShiftFill.FORWARD
    mixer_frequency: int = 44100      # sample rate
    mixer_size: int = -16            # 16-bit signed
    mixer_channels: int = 2           # stereo
    mixer_buffer: int = 512           # buffer size
    num_channels: int = 64            # max simultaneous sounds

# --- MIDI Interface ---
class MidiInterface:
    def __init__(self, input_name=None, output_name=None):
        self.input_name = input_name or mido.get_input_names()[0]
        self.output_name = output_name or mido.get_output_names()[0]

        self.inport = mido.open_input(self.input_name)
        self.outport = mido.open_output(self.output_name)

        logger.info(f"MIDI input: {self.input_name}")
        logger.info(f"MIDI output: {self.output_name}")

    def receive(self, block=False):
        msg = self.inport.receive() if block else self.inport.poll()
        if msg:
            logger.debug(f"Received: {msg}")
        return msg

    def close(self):
        self.inport.close()
        self.outport.close()
        logger.info("Closed MIDI ports")

# --- MIDI Sound Player ---
class MidiSoundPlayer:
    def __init__(self, config: MidiSoundConfig):
        self.config = config

        # High-performance mixer initialization
        pygame.mixer.pre_init(
            frequency=self.config.mixer_frequency,
            size=self.config.mixer_size,
            channels=self.config.mixer_channels,
            buffer=self.config.mixer_buffer
        )
        pygame.mixer.init()
        pygame.mixer.set_num_channels(self.config.num_channels)

        self.sounds = {}
        self._preload_sounds()
        if self.config.pitch_shift_fill != PitchShiftFill.OFF:
            self._fill_unassigned_keys()

    def _preload_sounds(self):
        for note, path in self.config.note_map.items():
            if path:
                if path.exists():
                    try:
                        self.sounds[note] = pygame.mixer.Sound(str(path))
                        logger.info(f"Loaded sound for note {note}: {path}")
                    except pygame.error as e:
                        logger.error(f"Could not load {path}: {e}")
                else:
                    logger.error(f"File not found: {path}")

    def _resample_sound(self, sound: pygame.mixer.Sound, semitone_shift: int):
        """Return a new Sound object pitch-shifted by semitone_shift half-steps."""
        arr = pygame.sndarray.array(sound)
        factor = 2 ** (semitone_shift / 12.0)
        new_length = int(arr.shape[0] / factor)

        if arr.ndim == 1:
            # Mono
            resampled = np.interp(
                np.linspace(0, arr.shape[0], new_length),
                np.arange(arr.shape[0]),
                arr
            ).astype(arr.dtype)
        else:
            # Stereo / multi-channel
            resampled = np.zeros((new_length, arr.shape[1]), dtype=arr.dtype)
            for ch in range(arr.shape[1]):
                resampled[:, ch] = np.interp(
                    np.linspace(0, arr.shape[0], new_length),
                    np.arange(arr.shape[0]),
                    arr[:, ch]
                ).astype(arr.dtype)

        return pygame.mixer.Sound(resampled)

    def _fill_unassigned_keys(self):
        all_notes = list(range(21, 109))  # Piano range
        assigned_notes = sorted(self.sounds.keys())
        logger.debug(f"Assigned notes before pitch fill: {assigned_notes}")

        if self.config.pitch_shift_fill == PitchShiftFill.FORWARD:
            for i, note in enumerate(assigned_notes):
                root_sound = self.sounds[note]
                next_note = assigned_notes[i + 1] if i + 1 < len(assigned_notes) else 109
                for fill_note in range(note + 1, next_note):
                    shift = fill_note - note
                    self.sounds[fill_note] = self._resample_sound(root_sound, shift)
                    logger.debug(f"Forward filled note {fill_note} from root {note} (+{shift} semitones)")

        elif self.config.pitch_shift_fill == PitchShiftFill.BACKWARD:
            for i in reversed(range(len(assigned_notes))):
                note = assigned_notes[i]
                root_sound = self.sounds[note]
                prev_note = assigned_notes[i - 1] if i > 0 else 21
                for fill_note in range(prev_note + 1, note):
                    shift = fill_note - note
                    self.sounds[fill_note] = self._resample_sound(root_sound, shift)
                    logger.debug(f"Backward filled note {fill_note} from root {note} ({shift} semitones)")

    def handle_midi_message(self, msg):
        if msg.type == 'note_on' and msg.velocity > 0:
            sound = self.sounds.get(msg.note)
            if sound:
                sound.play()
                logger.debug(f"Played sound for note {msg.note}")

    def set_note_map(self, new_map: dict):
        self.config.note_map = new_map
        self._preload_sounds()
        if self.config.pitch_shift_fill != PitchShiftFill.OFF:
            self._fill_unassigned_keys()

# --- Main ---
if __name__ == "__main__":
    config = MidiSoundConfig(
        note_map={
            62: SOUNDS_DIR / "awawa.mp3",
            64: SOUNDS_DIR / "Scratch 1.wav",
            65: SOUNDS_DIR / "Random Noise 1.wav",
            66: SOUNDS_DIR / "Vox 1.wav",
            67: SOUNDS_DIR / "Synth 1.wav",
            68: SOUNDS_DIR / "Synth 2.wav",
            69: SOUNDS_DIR / "chris.wav",
        },
        pitch_shift_fill=PitchShiftFill.FORWARD,
        num_channels=64
    )

    midi = MidiInterface()
    player = MidiSoundPlayer(config)

    logger.info("Listening for MIDI notes... (Ctrl+C to stop)")
    try:
        while True:
            msg = midi.receive()
            if msg:
                player.handle_midi_message(msg)
    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        midi.close()
        pygame.mixer.quit()

