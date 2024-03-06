#!/usr/bin/env python
"""
This script removes GPL packages.
Packages are hardcoded.
"""
import os
import pathlib

GPL_PACKAGES = ["math2html.py", "math.css", "rst.el"]

root_path = pathlib.Path(__file__).parent.parent.absolute()


def delete_package(filename: str) -> None:
    files = root_path.rglob(f"**/{filename}")
    if not files:
        print(f"Files {filename} does not exists.")
    for file in files:
        print(f"Removing file {file}")
        os.remove(file)


def main() -> None:
    for package in GPL_PACKAGES:
        delete_package(package)


if __name__ == "__main__":
    main()
