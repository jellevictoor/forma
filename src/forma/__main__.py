"""Entry point for the forma application.

Run with: uvicorn forma.__main__:app --host 0.0.0.0 --port 8080
Or:       python -m forma
"""

from forma.adapters.web.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
