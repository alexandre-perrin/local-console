#!/usr/bin/env python
"""
Downloads source code of tools.
"""
import json
import pathlib
import subprocess

root_path = pathlib.Path(__file__).parent.absolute()
target_folder = pathlib.Path() / "tools"


def main() -> None:
    with open(root_path / "manual-tools-sbom.json") as f:
        data = json.loads(f.read())

    for component in data["components"]:
        branch, url = None, None
        for ref in component["externalReferences"]:
            if ref["type"] == "code":
                url = ref["url"]
            elif ref["type"] == "branch":
                branch = ref["url"]
        if url and branch:
            name = component["bom-ref"]
            folder = str(target_folder / name)
            subprocess.run(
                ["git", "clone", "--branch", branch, "--depth", "1", url, folder]
            )
        else:
            print(f"{component['bom-ref']} is missing.")
            exit(1)


if __name__ == "__main__":
    main()
