#!/usr/bin/env python3
"""
EV Engine Initialization Script (Python version)
Cross-platform setup for the Antigravity EV Engine
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


# Colors for terminal output
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

    @classmethod
    def disable(cls):
        """Disable colors on Windows if not supported"""
        if platform.system() == 'Windows':
            cls.BLUE = cls.GREEN = cls.YELLOW = cls.RED = cls.NC = ''


def print_header():
    """Print welcome header"""
    print()
    print(f"{Colors.BLUE}╔═══════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.BLUE}║   Antigravity EV Engine - Setup      ║{Colors.NC}")
    print(f"{Colors.BLUE}╚═══════════════════════════════════════╝{Colors.NC}")
    print()


def check_python():
    """Step 1: Verify Python version"""
    print(f"{Colors.BLUE}[1/5]{Colors.NC} Checking Python installation...")
    version = sys.version_info

    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"{Colors.RED}✗ Python 3.8+ required (found {version.major}.{version.minor}){Colors.NC}")
        sys.exit(1)

    print(f"{Colors.GREEN}✓ Python {version.major}.{version.minor}.{version.micro} found{Colors.NC}")
    print()


def create_venv():
    """Step 2: Create virtual environment"""
    print(f"{Colors.BLUE}[2/5]{Colors.NC} Setting up virtual environment...")
    venv_path = Path("venv")

    if venv_path.exists():
        print(f"{Colors.YELLOW}! Virtual environment already exists, skipping...{Colors.NC}")
    else:
        subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
        print(f"{Colors.GREEN}✓ Virtual environment created{Colors.NC}")
    print()

    return venv_path


def get_pip_path(venv_path):
    """Get pip executable path for the virtual environment"""
    if platform.system() == 'Windows':
        return venv_path / "Scripts" / "pip.exe"
    else:
        return venv_path / "bin" / "pip"


def get_python_path(venv_path):
    """Get python executable path for the virtual environment"""
    if platform.system() == 'Windows':
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def install_dependencies(venv_path):
    """Step 3: Install Python dependencies"""
    print(f"{Colors.BLUE}[3/5]{Colors.NC} Installing dependencies...")

    pip_path = get_pip_path(venv_path)

    # Upgrade pip
    subprocess.run([str(pip_path), "install", "--upgrade", "pip", "-q"], check=True)

    # Install requirements
    requirements_path = Path("requirements.txt")
    if not requirements_path.exists():
        print(f"{Colors.RED}✗ requirements.txt not found{Colors.NC}")
        sys.exit(1)

    subprocess.run([str(pip_path), "install", "-r", "requirements.txt", "-q"], check=True)
    print(f"{Colors.GREEN}✓ Dependencies installed{Colors.NC}")
    print()


def configure_api_key():
    """Step 4: Set up .env file with API key"""
    print(f"{Colors.BLUE}[4/5]{Colors.NC} Configuring API settings...")

    env_path = Path(".env")

    if env_path.exists():
        print(f"{Colors.YELLOW}! .env file already exists{Colors.NC}")
        response = input("Do you want to update your API key? (y/N): ").strip().lower()
        if response not in ['y', 'yes']:
            print(f"{Colors.BLUE}Skipping API key configuration{Colors.NC}")
            print()
            return
        env_path.unlink()

    print()
    print(f"{Colors.YELLOW}You need an API key from The Odds API{Colors.NC}")
    print("Get one free at: https://the-odds-api.com/")
    print()

    api_key = input("Enter your Odds API key: ").strip()

    if not api_key:
        print(f"{Colors.YELLOW}! No API key entered. You can add it later to .env{Colors.NC}")
        env_path.write_text("ODDS_API_KEY=\n")
    else:
        env_path.write_text(f"ODDS_API_KEY={api_key}\n")
        print(f"{Colors.GREEN}✓ API key saved to .env{Colors.NC}")

    print()


def initialize_database(venv_path):
    """Step 5: Initialize SQLite database"""
    print(f"{Colors.BLUE}[5/5]{Colors.NC} Initializing database...")

    python_path = get_python_path(venv_path)

    try:
        result = subprocess.run(
            [str(python_path), "-c", "from src import db; db.initialize_db()"],
            check=True,
            capture_output=True,
            text=True
        )
        print(f"{Colors.GREEN}✓ Database ready{Colors.NC}")
    except subprocess.CalledProcessError:
        print(f"{Colors.YELLOW}! Database may already be initialized{Colors.NC}")

    print()


def print_next_steps():
    """Print success message and next steps"""
    print(f"{Colors.GREEN}╔═══════════════════════════════════════╗{Colors.NC}")
    print(f"{Colors.GREEN}║          Setup Complete! 🚀            ║{Colors.NC}")
    print(f"{Colors.GREEN}╚═══════════════════════════════════════╝{Colors.NC}")
    print()
    print(f"{Colors.BLUE}Next steps:{Colors.NC}")

    if platform.system() == 'Windows':
        print("  1. Activate the environment:")
        print(f"     {Colors.YELLOW}venv\\Scripts\\activate{Colors.NC}")
    else:
        print("  1. Activate the environment:")
        print(f"     {Colors.YELLOW}source venv/bin/activate{Colors.NC}")

    print()
    print("  2. Run the dashboard:")
    print(f"     {Colors.YELLOW}streamlit run dashboard.py{Colors.NC}")
    print()
    print("  3. Click 'Refresh Market' to fetch odds")
    print()
    print(f"{Colors.BLUE}Need help?{Colors.NC} Check BLUEPRINT.md for details")
    print()


def main():
    """Main initialization flow"""
    # Disable colors on Windows if needed
    if platform.system() == 'Windows':
        Colors.disable()

    try:
        print_header()
        check_python()
        venv_path = create_venv()
        install_dependencies(venv_path)
        configure_api_key()
        initialize_database(venv_path)
        print_next_steps()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Setup cancelled by user{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}✗ Setup failed: {e}{Colors.NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()
