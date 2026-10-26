import argparse
from pathlib import Path
import subprocess
import sys


SKILLS = ("track_face", "track_person", "detect_objects", "nod_yes", "shake_no")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Run a robot skill.")
    parser.add_argument("skill", choices=SKILLS)
    return parser.parse_args(argv)


def run(skill):
    from classes import Robot

    return getattr(Robot(), skill)()


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
        run(args.skill)
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        print(f"Robot could not run: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())




