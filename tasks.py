"""
Invoke Tasks.
"""
import os
import sys
import subprocess
import pathlib
from datetime import datetime
import zipfile
from invoke import task

NAME="ssm_manager"
VERSION_FILE = "ssm_manager/VERSION"
DIST_DIR = "dist"
RELEASE_DIR = "release"

@task
def bump_version(c):
    """Increases the version number in the VERSION file.
    The version format is expected to be MAJOR.MINOR.PATCH.

    MAJOR = Numerical value for Year
    MINOR = Numerical value for Month
    PATCH = Numerical value for Build Number
    """
    # pylint: disable=unused-variable
    year, month = datetime.now().strftime("%y/%-m").split("/")
    major, minor, patch = (0, 0, 0)
    try:
        with open(VERSION_FILE, "r", encoding='utf-8') as f:
            version = f.read().strip()
            major, minor, patch = map(int, version.split('.'))
        print(f"Current version: {major}.{minor}.{patch}")

        if int(major) != int(year) or int(minor) != int(month):
            major = year
            minor = month
            patch = 0
        patch += 1
        new_version = f"{major}.{minor}.{patch}"
    except FileNotFoundError:
        new_version = f"{year}.{month}.{patch}"

    with open(VERSION_FILE, "w", encoding='utf-8') as f:
        f.write(new_version + "\n")
    print(f"Version updated to: {new_version}")


@task
def build(c):
    """Builds the executable using PyInstaller."""
    # pylint: disable=unused-argument
    print("Starting build...")
    static_dir = pathlib.Path("ssm_manager", "static")
    templates_dir = pathlib.Path("ssm_manager", "templates")
    favicon_path = static_dir / "favicon.ico"
    version_path = pathlib.Path(VERSION_FILE)
    command = ["pyinstaller", "--onedir", "--noconsole", "--clean", "--noconfirm",
               '--add-data', f'{version_path}:ssm_manager/VERSION',
               '--add-data', f'{static_dir}:ssm_manager/static',
               '--add-data', f'{templates_dir}:ssm_manager/templates',
               f'--icon={favicon_path}',
               f'--name={NAME}',
               'main.py']
    subprocess.run(command, check=True)
    print("Build completed successfully.")


@task(pre=[build])
def package(c):
    """Use 7z cli to create a self-extracting archive."""
    # pylint: disable=unused-argument
    print("Creating package...")
    dist_dir = pathlib.Path(DIST_DIR)
    release_dir = pathlib.Path(RELEASE_DIR)
    os.makedirs(release_dir, exist_ok=True)
    version = ""
    with open(VERSION_FILE, "r", encoding='utf-8') as f:
        version = f.read().strip()
    archive_name = f"{NAME}_{version}.zip"
    archive_path = release_dir / archive_name
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in dist_dir.rglob('*'):
            if file.is_file():
                archive.write(file, os.path.relpath(file, dist_dir))

    print(f"Package created: {archive_path}")


@task
def run(c, api=False):
    """Runs the application."""
    # pylint: disable=unused-argument
    command = [sys.executable, "main.py"]
    if api:
        command.append("--api")
    subprocess.run(command, check=True)
