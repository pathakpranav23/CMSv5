from cms_app import create_app
import os

app = create_app()

if __name__ == "__main__":
    # Run the development server (allow PORT override for parallel previews)
    port = 5000
    try:
        port = int(os.environ.get("PORT", "5000"))
    except Exception:
        port = 5000
    app.run(host="127.0.0.1", port=port, debug=True)