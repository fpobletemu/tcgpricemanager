"""
Creates a Windows desktop shortcut for TCG Price Manager.
Run once after setting up the virtual environment:
    python setup_shortcut.py
"""
import os
import sys
import subprocess
from pathlib import Path


def create_shortcut():
    project_dir = Path(__file__).resolve().parent
    pythonw     = project_dir / ".venv" / "Scripts" / "pythonw.exe"
    main_py     = project_dir / "tcg_app" / "main.py"
    icon_file   = project_dir / "tcg_app" / "assets" / "icon.ico"
    desktop     = Path(os.environ.get("USERPROFILE", Path.home())) / "Desktop"
    shortcut    = desktop / "TCG Price Manager.lnk"

    if not pythonw.exists():
        print("ERROR: Virtual environment not found.")
        print("  Run first:")
        print("    python -m venv .venv")
        print("    .venv\\Scripts\\pip install -r requirements.txt")
        sys.exit(1)

    if not icon_file.exists():
        print("Generating icon...")
        subprocess.run(
            [str(project_dir / ".venv" / "Scripts" / "python.exe"),
             str(project_dir / "generate_icon.py")],
            check=True,
        )

    # Escape backslashes for PowerShell string
    ps = f"""
$ws = New-Object -ComObject WScript.Shell
$s  = $ws.CreateShortcut('{shortcut}')
$s.TargetPath       = '{pythonw}'
$s.Arguments        = '"{main_py}"'
$s.WorkingDirectory = '{project_dir}'
$s.IconLocation     = '{icon_file}'
$s.Description      = 'TCG Price Manager — catalog and pricing tool'
$s.Save()
Write-Host "OK"
""".strip()

    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"Shortcut created: {shortcut}")
        print("You can now launch the app by double-clicking the desktop icon.")
    else:
        print(f"ERROR creating shortcut:\n{result.stderr}")
        sys.exit(1)


if __name__ == "__main__":
    create_shortcut()
