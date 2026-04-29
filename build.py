import os
import shutil
import subprocess
import sys
from pathlib import Path

def main():
    base_dir = Path(__file__).parent
    dist_dir = base_dir / "dist"
    build_dir = base_dir / "build"

    skip = os.getenv("OBFUSCATE_BUILD", "1") == "0"

    print("=" * 60)
    print("SQLManager Build System")
    print("=" * 60)

    # clean
    for d in [dist_dir, build_dir]:
        if d.exists():
            shutil.rmtree(d)

    # build normal wheel
    print("[1] Building wheel...")
    subprocess.run([sys.executable, "-m", "build", "--wheel"], check=True)

    if not skip:
        print("[2] Running PyArmor...")

        obf_dir = build_dir / "obf"
        subprocess.run([
            "pyarmor",
            "gen",
            "-O", str(obf_dir),
            str(base_dir / "SQLManager")
        ], check=True)

        print("[OK] Obfuscation done")

        # rebuild wheel (opcional dependendo estratégia)
        print("[3] Rebuilding wheel...")
        shutil.rmtree(dist_dir)
        subprocess.run([sys.executable, "-m", "build", "--wheel"], check=True)

    print("\n[SUCCESS] Done")

if __name__ == "__main__":
    sys.exit(main())