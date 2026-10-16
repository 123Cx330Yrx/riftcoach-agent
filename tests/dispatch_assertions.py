"""Check dispatch command prefixes without rejecting POSIX /bin/python."""
from pathlib import PurePosixPath, PureWindowsPath
import shlex


def assert_dispatch_python(text, executable, platform, *, command_count):
    executable = str(executable)
    if platform == 'win32':
        assert PureWindowsPath(executable).is_absolute()
        prefix = "& '" + executable.replace("'", "''") + "'"
    else:
        assert PurePosixPath(executable).is_absolute()
        prefix = shlex.quote(executable)
    commands = [line.strip() for line in text.splitlines() if ' -m ' in line]
    assert len(commands) == command_count
    assert all(line.startswith(prefix + ' -m scripts.') for line in commands), commands
