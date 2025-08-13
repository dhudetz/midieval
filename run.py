import mido
import pygame
import os
import logging
from dataclasses import dataclass


# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)


class MidiInterface:
    def __init__(self, input_name=None, output_name=None):
        self.input_name = input_name or mido.get_input_names()[0]
        self.output_name = output_name or mido.get_output_names()[0]
        
        self.inport = mido.open_input(self.input_name)
        self.outport = mido.open_output(self.output_name)

        logger.info(f"MIDI input: {self.input_name}")
        logger.info(f"MIDI output: {self.output_name}")

    def send(self, message_type, **kwargs):
        msg = mido.Message(message_type, **kwargs)
        self.outport.send(msg)
        logger.debug(f"Sent: {msg}")

    def receive(self, block=False):
        msg = self.inport.receive() if block else self.inport.poll()
        if msg:
            logger.debug(f"Received: {msg}")
        return msg

    def list_ports(self):
        ports = {
            "inputs": mido.get_input_names(),
            "outputs": mido.get_output_names()
        }
        logger.debug(f"Available ports: {ports}")
        return ports

    def close(self):
        self.inport.close()
        self.outport.close()
        logger.info("Closed MIDI ports")


@dataclass
class MidiSoundConfig:
    note_map: dict  # {note_number: "path/to/file.mp3"}


class MidiSoundPlayer:
    def __init__(self, config: MidiSoundConfig):
        self.config = config
        pygame.mixer.init()
        self.sounds = {}
        self._preload_sounds()

    def _preload_sounds(self):
        """Preload sounds into memory for instant playback."""
        for note, path in self.config.note_map.items():
            if path:
                if os.path.exists(path):
                    try:
                        self.sounds[note] = pygame.mixer.Sound(path)
                        logger.info(f"Loaded sound for note {note}: {path}")
                    except pygame.error as e:
                        logger.error(f"Could not load {path}: {e}")
                else:
                    logger.error(f"File not found: {path}")

    def handle_midi_message(self, msg):
        """Play a sound for a given MIDI note."""
        if msg.type == 'note_on' and msg.velocity > 0:
            sound = self.sounds.get(msg.note)
            if sound:
                sound.play()
                logger.debug(f"Played sound for note {msg.note}")

    def set_note_map(self, new_map: dict):
        self.config.note_map = new_map
        self._preload_sounds()


if __name__ == "__main__":
    config = MidiSoundConfig(
        note_map={
            60: "sounds/birthday.mp3",
            62: "sounds/awawa.mp3",
            64: "sounds/Scratch 1.wav",
            65: "sounds/Random Noise 1.wav",
            66: "sounds/Vox 1.wav",
            67: "sounds/Synth 1.wav",
            68: "sounds/Synth 2.wav",
        }
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

