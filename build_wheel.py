import shutil
import subprocess
import sys
from pathlib import Path


def main():
    base_dir = Path(__file__).parent
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"

    print("=" * 60)
    print("SQLManager Build System")
    print("=" * 60)

    for d in [dist_dir, build_dir]:
        if d.exists():
            shutil.rmtree(d)

    print("[1] Building wheel with Cython...")
    subprocess.run([sys.executable, "-m", "build", "--wheel"], check=True)

    print("\n[SUCCESS] Done")


if __name__ == "__main__":
    sys.exit(main())