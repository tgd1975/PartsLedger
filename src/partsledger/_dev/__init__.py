"""Internal-only developer tooling for PartsLedger.

Members of ``partsledger._dev`` are **not** part of the package's
public API. They exist so `scripts/*.py` shims and CI can call into
in-package implementations without those implementations being
discoverable from `from partsledger import …`.

Reorganising or removing anything under this subpackage does not
trigger a MAJOR semver bump (see ``RELEASING.md``).
"""
