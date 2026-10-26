import argparse
from contextlib import nullcontext
from pathlib import Path
import subprocess
import sys


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Face or person tracking with a Pico.")
    parser.add_argument("--detector", choices=("face", "person"), default="face")
    parser.add_argument("--source", choices=("percipio", "webcam"), default="percipio")
    parser.add_argument("--camera", type=int, default=0, help="Webcam index")
    parser.add_argument("--port", help="Pico serial port (auto-detected if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without moving servos")
    parser.add_argument("--debug-timing", action="store_true", help="Print controller update rate")
    return parser.parse_args(argv)


def run(args):
    from controller import TargetController
    from send_to_pico import PICOS
    from person_tracker import run_tracking

    if args.detector == "face":
        from face_detector import FaceDetector

        detector = FaceDetector()
    else:
        from person_detection import PersonDetector

        detector = PersonDetector()

    connection = nullcontext(None) if args.dry_run else PICOS["left_arm"]
    if not args.dry_run and args.port is not None:
        connection.port = args.port
    with connection as pico:
        controller = TargetController(pico, debug_timing=args.debug_timing)
        if pico is not None:
            pico.send_angles(controller.angle_x, controller.angle_y)
            print(f"Sending servo angles to {pico.port}. Press Q in the camera window to stop.")
        run_tracking(detector, source=args.source, camera_index=args.camera,
                     on_target=controller.update)


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
        print(f"Tracker could not run: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

