"""OS integration: open files and reveal them in the file manager."""
import os
import platform
import subprocess


class OperatingSystem:
    def __init__(self):
        self.name = platform.system()

    @property
    def is_mac(self):
        return self.name == "Darwin"

    def open(self, path):
        """Open a file/folder with the OS default application."""
        if self.name == "Windows":
            os.startfile(path)  # noqa: S606
        elif self.is_mac:
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)

    def reveal(self, path):
        """Show a file in Finder/Explorer/file manager."""
        if self.name == "Windows":
            subprocess.run(["explorer", "/select,", str(path)], check=False)
        elif self.is_mac:
            subprocess.run(["open", "-R", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path.parent)], check=False)
