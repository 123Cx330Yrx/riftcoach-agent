"""Framework-neutral runtime contracts for RiftCoach.

Keep this package initializer deliberately light.  Concrete runtime modules
import Skill and Harness contracts, so re-exporting them here would create an
easy circular-import path when observers are connected in 5E-2.
"""
