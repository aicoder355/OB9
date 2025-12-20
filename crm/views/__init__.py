"""Views package for crm app.

Expose the original monolithic views via `_legacy` so existing imports
that expect `crm.views.<name>` continue to work during incremental refactor.
Also expose the new smaller modules `exports` and `drivers`.
"""

"""
Load the original monolithic `crm/views.py` into this package namespace to
preserve backward compatibility while we incrementally split views into
smaller modules.
"""

import importlib.util
from pathlib import Path

monolith_path = Path(__file__).parent.parent / 'views.py'
# import the new submodules first so their names are available and won't be
# accidentally overwritten when we copy attributes from the monolithic file.
from . import exports, drivers_views

if monolith_path.exists():
	try:
		spec = importlib.util.spec_from_file_location('crm._monolith_views', str(monolith_path))
		monolith = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(monolith)
		# copy public attributes from monolith into package globals, but avoid
		# overwriting the `exports` and `drivers` module names which are real submodules.
		for name, value in vars(monolith).items():
				if not name.startswith('_') and name not in (
					'exports', 'drivers_views', 'orders', 'clients', 'containers', 'api',
					'drivers_admin', 'loyalty', 'notifications_views', 'telegram_integration'
				):
					globals()[name] = value
	except Exception:
		# If loading fails, allow import to continue; errors will surface in tests.
		pass

__all__ = ["exports", "drivers_views"]
