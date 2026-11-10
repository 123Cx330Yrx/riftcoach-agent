"""Explicit module-local dependency routing for prospective frozen-code reuse.

No sys.modules aliases for public modules and no process-wide import patch.
The two legacy modules import one another inside functions; routing those
imports locally avoids copying their state machine or changing old replay.
"""
import builtins
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
from uuid import uuid4


def private_module(path, dependencies):
    name = 'scripts._full_chain_' + uuid4().hex
    spec = importlib.util.spec_from_file_location(name, Path(path))
    module = importlib.util.module_from_spec(spec)

    def local_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and fromlist:
            if name in dependencies:
                return dependencies[name]
            selected = {part: dependencies[name + '.' + part] for part in fromlist
                        if name + '.' + part in dependencies}
            if selected:
                original = builtins.__import__(name, globals, locals, fromlist, level)
                return SimpleNamespace(**{part: selected.get(part, getattr(original, part, None))
                                          for part in fromlist})
        return builtins.__import__(name, globals, locals, fromlist, level)

    module.__dict__['__builtins__'] = dict(vars(builtins), __import__=local_import)
    sys.modules[spec.name] = module  # Needed by dataclasses/Pydantic annotations.
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module
