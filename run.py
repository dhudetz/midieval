import mido

class MidiInterface:
    def __init__(self, input_name=None, output_name=None):
        self.input_name = input_name or mido.get_input_names()[0]
        self.output_name = output_name or mido.get_output_names()[0]
        
        self.inport = mido.open_input(self.input_name)
        self.outport = mido.open_output(self.output_name)

    def send(self, message_type, **kwargs):
        """Send a MIDI message."""
        msg = mido.Message(message_type, **kwargs)
        self.outport.send(msg)

    def receive(self, block=False):
        """Receive one MIDI message (blocking or non-blocking)."""
        if block:
            return self.inport.receive()
        else:
            msg = self.inport.poll()
            return msg

    def list_ports(self):
        """List available ports."""
        return {
            "inputs": mido.get_input_names(),
            "outputs": mido.get_output_names()
        }

    def close(self):
        self.inport.close()
        self.outport.close()

if __name__ == "__main__":
    midi = MidiInterface()

    # Send a note on/off
    midi.send('note_on', note=60, velocity=100)   # Middle C on
    midi.send('note_off', note=60, velocity=100)  # Middle C off

    # Check for incoming MIDI without blocking
    while True:
        msg = midi.receive()
        if msg:
            print("Received:", msg)

    # List ports
    print(midi.list_ports())

    # Close when done
    midi.close()
