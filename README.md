# LifeOS Twin frontend

A dependency-light static frontend. Three.js is loaded from jsDelivr at runtime, so a browser needs internet access to load the 3D library. No Node build step is required.

## Preview

Open `index.html` in a modern browser with WebGL enabled. The interactive city scene works independently of the API. Scenario simulation and knowledge search require the FastAPI backend.

## Connect the backend

Start the backend on `http://127.0.0.1:8000`, then open the page in a browser. The frontend uses that URL by default. To change it, define `window.LIFEOS_API_URL` before loading `app.js`.

The API allows cross-origin requests for this prototype. Do not keep wildcard CORS for a production deployment; restrict it to the exact frontend origin.

## GitHub Pages

The repository workflow at `.github/workflows/pages.yml` publishes this static frontend when changes are pushed to `main`. GitHub Pages hosts the visual frontend only. It does not host the Python backend, so scenario and knowledge features need a separately hosted API. This project intentionally does not use a paid hosting service.
