from pathlib import Path
import subprocess
import sys


def main():
    project_dir = Path(__file__).resolve().parent
    python = project_dir / ".venv" / "Scripts" / "python.exe"
    if not python.is_file():
        print(f"Project Python environment not found: {python}", file=sys.stderr)
        return 1
    
    if Path(sys.executable).resolve() != python.resolve():
        try:
            return subprocess.call(
                [str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
                cwd=project_dir,
            )
        except KeyboardInterrupt:
            return 130

    try:
        from Communicate_pico import main as run_tracking
        #from face_recognition import main as track_target
        from person import main as track_target
        run_tracking(track_face=track_target)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Tracker could not run: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
