"""Guarded direct-patch worker identity; frozen stream/observation IO reused privately."""
from scripts import review_duty_patch_execution as execution
from scripts.full_chain_modules import private_module

_transport = private_module(execution.ROOT/'scripts/review_duty_transport.py',
    {'scripts.review_duty_execution': execution})
_transport.VERSION = 'direct-patch-observed-v1'
_transport.REVIEW = 'direct-patch-glm53-high-time600-v1'
_transport.TRANSPORTS = (_transport.REVIEW,)


def check_execution_guard(guard, prepared):
    if guard is None:
        raise ValueError('direct_patch_transport_guard_required')
    from scripts.review_duty_patch_launch import require_guard
    require_guard(*guard, prepared=prepared)


_transport.check_execution_guard = check_execution_guard
_attach = _transport.attach_observation


def attach_observation(bridge, **kwargs):
    child = bridge.run_child
    def run_child(command, raw, **options):
        command = list(command)
        at = command.index('-m') + 1
        if command[at] != 'scripts.review_duty_transport':
            raise ValueError('direct_patch_transport_entrypoint')
        command[at] = 'scripts.review_duty_patch_transport'
        return child(command, raw, **options)
    bridge.run_child = run_child
    return _attach(bridge, **kwargs)


_transport.attach_observation = attach_observation
Sender, verify, main = _transport.Sender, _transport.verify, _transport.main


if __name__ == '__main__':
    main()
