import math
import os
import struct
import wave

def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, "wav")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "switch.wav")
    rate = 8000
    n = int(rate * 0.08)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            v = int(128 + 80 * math.sin(i * 2 * math.pi * 880 / rate) * (1 - i / n))
            frames.append(max(0, min(255, v)))
        w.writeframes(bytes(frames))
    print("Wrote", path)


if __name__ == "__main__":
    main()
