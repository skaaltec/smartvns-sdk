from smartvns.vnsconnect import Stimulator
from smartvns.config import StimConfig
import asyncio
import sys
from smartvns.utils import Decoder
from smartvns.logger import DataLogger


def read_key():
    """Read one keystroke. Returns 'UP'/'DOWN'/'LEFT'/'RIGHT' for arrows, else the char."""
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            ch2 = msvcrt.getwch()
            return {"H": "UP", "P": "DOWN", "K": "LEFT", "M": "RIGHT"}.get(ch2, "")
        return ch
    import tty
    import termios
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
        if ch == "\x1b":
            seq = sys.stdin.read(2)
            return {"[A": "UP", "[B": "DOWN", "[D": "LEFT", "[C": "RIGHT"}.get(seq, "")
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

"""
Options to connect to SmartVNS devices:

Options:
1. Connect via knon device alias 
  stim = Stimulator("AA:BB:CC:DD:EE:FF")
2. Run Scanner function 
    scanner = vnsconnect.Scanner()
    scanner.start()
    await asyncio.sleep(5)  # Scan for 5 seconds
    scanner.stop()


"""

async def connect():

    stim = Stimulator("CB8E7E61-3674-75A3-6E1B-E347A13B3F5D")
    stim.connect()
    decoder = Decoder()
    logger = DataLogger("log.txt")

    def callback(data: bytearray):
        samples = decoder(data)
        logger(samples)

    stim.start_notification(callback)
    print("Connected to stimulator.")
    cfg = StimConfig(**{
      "retain_cfg": False,
      "trigger_ms": 1000,
      "forward_us": 250,
      "deadband_us": 100,
      "period_us": 40000,
      "intensity_uA": 100,
    })

    stim.set_stim_config(cfg)
    current_config = stim.get_stim_config()
    print("\nCurrent stimulation configuration:")
    print(f"   Intensity: {current_config.intensity_uA} µA")


    print("Logging incoming samples to log.txt")

    try:
        while True:

            key = read_key()

            if key == " ":  # Spacebar pressed
                print("Stimulation triggered!")
                stim.trigger(duration_ms=1000)
                print(
                    f"   Current intensity: {stim.get_stim_config().intensity_uA} µA")

            elif key.lower() == "d":
                cfg = stim.get_stim_config()
                freq_hz = max(1_000_000 / cfg.period_us - 5, 1)
                cfg.period_us = int(round(1_000_000 / freq_hz))
                stim.set_stim_config(cfg)
                print(f"   Frequency: {1_000_000 / cfg.period_us:.1f} Hz")

            elif key.lower() == "i":
                cfg = stim.get_stim_config()
                freq_hz = min(1_000_000 / cfg.period_us + 5, 100)
                cfg.period_us = int(round(1_000_000 / freq_hz))
                stim.set_stim_config(cfg)
                print(f"   Frequency: {1_000_000 / cfg.period_us:.1f} Hz")

            elif key == "UP":
                cfg = stim.get_stim_config()
                cfg.intensity_uA = min(cfg.intensity_uA + 100, 5000)
                stim.set_stim_config(cfg)
                print(f"   Intensity: {cfg.intensity_uA} µA")

            elif key == "DOWN":
                cfg = stim.get_stim_config()
                cfg.intensity_uA = max(cfg.intensity_uA - 100, 100)
                stim.set_stim_config(cfg)
                print(f"   Intensity: {cfg.intensity_uA} µA")

            elif key.lower() == "q":  # Quit
                print("\nExiting...")
                break
            else:
                print(
                    f"Unknown input: {key!r} (SPACE=trigger, i/d=frequency ±5 Hz, UP/DOWN=intensity ±100, q=quit)")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    finally:
        print("Stopping notifications...")
        try:
            stim.stop_notification()
        except Exception as e:
            print(f"   stop_notification error: {e}")
        print("Closing logger...")
        logger.close()
        print("Disconnecting...")
        stim.disconnect()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(connect())