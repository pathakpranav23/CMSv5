"""SA2 compatibility shim — loaded before cms_app import in tests/conftest.py.

Problem:
  Flask-SQLAlchemy 2.5.1 does `for key in module.__all__: setattr(self, key, obj)`
  for `sqlalchemy`, `sqlalchemy.orm`, and `sqlalchemy.sql` at init time.
  SQLAlchemy 2.0 removed all the `__all__` attributes, and several attribute
  names (`engine`, `url`, `inspect`, `MetaData`, orm properties etc.) collide
  with Flask-SQLAlchemy's own descriptors — triggering calls like `self.engine`
  which require an app context at SQLAlchemy() construction time.

Fix:
  (1) Force the lazy submodule imports,
  (2) Build sane __all__ lists that EXCLUDE names colliding with FSA class attrs,
  (3) Monkey-patch `_include_sqlalchemy` on Flask-SQLAlchemy to be permissive.
"""
import sys

try:
    import sqlalchemy as _sa
except Exception:  # pragma: no cover - sqlalchemy not importable
    _sa = None


def _install():
    if _sa is None:
        return

    # 1. Force imports of the submodules FSA2 walks
    for _name in ("orm", "sql", "event", "exc", "schema", "types", "dialects", "util"):
        try:
            __import__(f"sqlalchemy.{_name}")
        except Exception:
            pass

    # 2. Patch Flask-SQLAlchemy's _include_sqlalchemy to be tolerant
    try:
        from flask_sqlalchemy import SQLAlchemy as _FSA, __init__ as _fsa_init
    except Exception:
        return

    _COLLIDE_BLACKLIST = set()  # built dynamically below, see for loop

    try:
        from flask_sqlalchemy import _include_sqlalchemy as _orig  # 2.x style
    except Exception:
        _orig = None

    # Precompute names that FSA already exposes as descriptors/properties.
    # These MUST NOT be overwritten with plain sqlalchemy module references
    # (in particular `engine`, `url`, `metadata`, `session` which require
    # an app context or bind an existing attribute we depend on).
    try:
        from flask_sqlalchemy import SQLAlchemy as _FSA2
        import inspect as _inspect
        _UNSAFE = set()
        for _n in dir(_FSA2):
            if _n.startswith("_"):
                continue
            try:
                _attr = getattr(_FSA2, _n, None)
            except Exception:
                # Property that requires app context (engine, url, etc.)
                _UNSAFE.add(_n)
                continue
            if _inspect.isdatadescriptor(_attr) or _inspect.ismethod(_attr) or _inspect.isfunction(_attr):
                _UNSAFE.add(_n)
        _COLLIDE_BLACKLIST = _UNSAFE
    except Exception:
        _COLLIDE_BLACKLIST = {"engine", "url", "metadata", "session", "make_connector", "create_engine"}

    def _patched_include(db, query_class=None):
        import sqlalchemy
        modules = [(sqlalchemy, None)]
        try:
            import sqlalchemy.orm  # noqa
            import sqlalchemy.sql  # noqa
            modules.append((sqlalchemy.orm, None))
            modules.append((sqlalchemy.sql, None))
        except Exception:
            pass
        for module, _prefix in modules:
            all_list = getattr(module, "__all__", None)
            if all_list is None:
                all_list = [n for n in dir(module) if not n.startswith("_")]
            for key in all_list:
                # Always copy type-aliases like Column/Integer even if dir(db) shows them:
                # some may be absent entirely if the FSA class only references them via engine.
                if key in _COLLIDE_BLACKLIST:
                    continue
                try:
                    obj = getattr(module, key)
                except Exception:
                    continue
                # Skip things that are ALREADY on db (e.g. as callable methods
                # or cached property values) unless they are missing types.
                if hasattr(db, key):
                    continue
                try:
                    setattr(db, key, obj)
                except Exception:
                    pass

    if _orig is not None:
        # Inject replacement in flask_sqlalchemy module scope
        import flask_sqlalchemy as _fsa
        _fsa._include_sqlalchemy = _patched_include
    else:
        # Fallback: patch via FSA class by rewriting __init__
        _old_init = _FSA.__init__

        def _new_init(self, *a, **kw):
            import flask_sqlalchemy as _fsa_loc
            _saved = getattr(_fsa_loc, "_include_sqlalchemy", None)
            _fsa_loc._include_sqlalchemy = _patched_include
            try:
                _old_init(self, *a, **kw)
            finally:
                if _saved is not None:
                    _fsa_loc._include_sqlalchemy = _saved

        _FSA.__init__ = _new_init

    # --- SignalSession.get_bind signature fix for SA2 -----------------------
    # FSA 2.5.1 overrides get_bind(self, mapper=None, clause=None) and calls
    # SessionBase.get_bind(self, mapper, clause) with 2 positional args.
    # SA2 renamed / changed the signature: Session.get_bind() no longer
    # accepts positional clause, so adapter the call to SA2's API.
    try:
        import flask_sqlalchemy as _fsa_loc2
        from sqlalchemy.orm import Session as _SASession

        _old_get_bind = _fsa_loc2.SignallingSession.get_bind

        def _sa2_get_bind(self, mapper=None, clause=None, **_kw):
            if mapper is not None:
                try:
                    persist_selectable = mapper.persist_selectable
                except AttributeError:
                    persist_selectable = mapper.mapped_table
                info = getattr(persist_selectable, "info", {})
                bind_key = info.get("bind_key")
                if bind_key is not None:
                    from flask_sqlalchemy import get_state as _gs
                    _state = _gs(self.app)
                    return _state.db.get_engine(self.app, bind=bind_key)
            # Call SA2's Session.get_bind with keyword args only
            return _SASession.get_bind(self, mapper=mapper, clause=clause, **_kw)

        _fsa_loc2.SignallingSession.get_bind = _sa2_get_bind
    except Exception:
        pass


_install()
