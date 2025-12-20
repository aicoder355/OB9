from django.apps import AppConfig
import warnings


class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'
    def ready(self):
        # Import signals to connect them
        try:
            from . import signals  # noqa: F401
        except Exception:
            # Avoid raising errors during migrations or import-time issues
            pass

        # Runtime compatibility: some Python/Django combinations may raise
        # AttributeError inside `Context.__copy__` (observed on Python 3.14).
        # Apply a minimal, scoped fallback only if the default copy fails.
        try:
            from django.template import context as template_context
            Context = template_context.Context

            # Test current Context.__copy__ behavior
            try:
                ctx = Context()
                _ = ctx.__copy__()
            except Exception as exc:
                # Only patch when copy raises the problematic AttributeError
                warnings.warn(f"Applying Context.__copy__ fallback due to: {exc}")

                def _context_copy(self):
                    # Attempt to create a shallow copy preserving render_context
                    try:
                        new = template_context.Context()
                        # For Django versions with .dicts
                        if hasattr(self, 'dicts'):
                            try:
                                new.dicts = list(self.dicts)
                            except Exception:
                                pass
                        # Preserve render_context if present
                        if hasattr(self, 'render_context'):
                            try:
                                new.render_context = getattr(self, 'render_context')
                            except Exception:
                                pass
                        return new
                    except Exception:
                        # Final fallback: create Context from flattened data
                        try:
                            if hasattr(self, 'flatten'):
                                return template_context.Context(self.flatten())
                            return template_context.Context(dict(self))
                        except Exception:
                            return template_context.Context()

                try:
                    Context.__copy__ = _context_copy
                except Exception:
                    # If we cannot assign, just skip the patch to avoid breaking startup
                    warnings.warn('Could not assign Context.__copy__ fallback; skipping')
        except Exception:
            # If django.template is unavailable (e.g., during some migration phases), skip
            pass
