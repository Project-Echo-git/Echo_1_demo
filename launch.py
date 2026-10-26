import argparse
from pathlib import Path
import subprocess
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run a robot capability.")
    parser.add_argument("--skill", "--detector", dest="skill",
                        choices=("face", "person", "objects"), default="face")
    parser.add_argument("--source", choices=("percipio", "webcam"), default="percipio")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index")
    parser.add_argument("--port", help="Pico serial port (auto-detected if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without moving servos")
    parser.add_argument("--debug-timing", action="store_true", help="Print controller update rate")
    return parser.parse_args(argv)


def run(args):
    from classes import Robot

    robot = Robot(source=args.source, camera_index=args.camera, port=args.port,
                  dry_run=args.dry_run, debug_timing=args.debug_timing)
    skills = {
        "face": robot.track_face,
        "person": robot.track_person,
        "objects": robot.object_detection,
    }
    return skills[args.skill]()


def main():
    args = parse_args()
    project_dir = Path(__file__).resolve().parent
    python = project_dir / ".venv" / "Scripts" / "python.exe"
    if not python.is_file():
        print(f"Project Python environment not found: {python}", file=sys.stderr)
        return 1
    try:
        if Path(sys.executable).resolve() != python.resolve():
            return subprocess.call([str(python), str(Path(__file__).resolve()), *sys.argv[1:]],
                                   cwd=project_dir)
        run(args)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Robot could not run: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())




