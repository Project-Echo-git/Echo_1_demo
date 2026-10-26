"""
    python launch.py                 # Camera + face tracking + Pico
    python launch.py --dry-run       # Preview without Pico commands
    python launch.py --port COM5     # Choose the Pico serial port

"""
from pathlib import Path
import subprocess
import sys


def main():
    project_dir = Path(__file__).resolve().parent
    python = project_dir / ".venv" / "Scripts" / "python.exe"
    if not python.is_file():
        print(f"Project Python environment not found: {python}", file=sys.stderr)
        return 1

    # Relaunch with the project's SDK dependencies even when started with a
    # different Python installation or from another working directory.
    if Path(sys.executable).resolve() != python.resolve():
        try:
            return subprocess.call(
                [str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
                cwd=project_dir,
            )
        except KeyboardInterrupt:
            return 130

    try:
        # This module connects face_recognition -> percipio_camera and sends
        # the detected face offsets to the Pico. Reuse its command-line options.
        from Communicate_pico import main as run_tracking
        run_tracking()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Face tracker could not run: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
