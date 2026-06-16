import os
from cms_app import create_app
from cms_app.route_overrides import route_overrides_bp


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return (raw or "").strip().lower() in {"1", "true", "yes", "on"}


DEBUG_ENABLED = _env_flag("FLASK_DEBUG", default=False)
os.environ.setdefault("CMS_STARTUP_SCHEMA_SYNC", "1" if DEBUG_ENABLED else "0")

app = create_app()
app.register_blueprint(route_overrides_bp)

if __name__ == "__main__":
    # Run the development server (allow PORT override for parallel previews)
    port = 5000
    try:
        port = int(os.environ.get("PORT", "5000"))
    except Exception:
        port = 5000
    app.run(host="127.0.0.1", port=port, debug=DEBUG_ENABLED, use_reloader=DEBUG_ENABLED)
