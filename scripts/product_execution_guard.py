"""Outer-launcher checks must pause, never become a semantic rejection."""
from pathlib import Path

from app.evaluation.sol_natural_session import SessionBlocked, digest


def verify_locked_inventory(session, inventory):
    if not session._open:
        raise SessionBlocked('product_guard_session_not_owned')
    session.verify()
    lock = session.root.with_name(session.root.name+'.lock').resolve()
    for name, pin in inventory.items():
        path = Path(name)
        # The OS mutex is verified before/after execution when unlocked. It is
        # not a business artifact; Windows denies read_bytes while held.
        if path.resolve() == lock:
            continue
        if digest(path.read_bytes()) != pin:
            raise ValueError('product_guard_inherited_file_changed')


def checked(action, record_error):
    try:
        return action()
    except Exception as error:
        # No request text, credentials, or arbitrary exception message is saved.
        try:
            record_error(dict(exception_type=type(error).__name__, new_model_request=False))
        finally:
            raise SessionBlocked('product_launcher_guard_failed') from error
