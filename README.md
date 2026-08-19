# Nathan Woodburn's Website (`nathan.woodburn.au`)

Personal website, portfolio, interactive resume, blog, and API server for [nathan.woodburn.au](https://nathan.woodburn.au)

The canonical repository is hosted on [git.woodburn.au](https://git.woodburn.au) with a public mirror on [GitHub](https://github.com/Nathanwoodburn/Nathanwoodburn.github.io).

---

## Features

- **Dynamic & Config-Driven Resume**:
  - Structured content managed via [`data/resume.json`](data/resume.json).
  - Responsive layout with desktop centering and mobile-first design.
  - Automatic dark mode support (`prefers-color-scheme: dark` and `data-bs-theme="dark"`).
  - On-demand and build-time 1-page A4 PDF generation via headless Chromium (`/resume.pdf` and `/resume.pdf?support=1`).
- **Terminal & CLI Friendly**:
  - Native `curl` and `finger` terminal views with custom ASCII art, system info, and plain-text output.
- **Blog & "Now" Updates**:
  - Date-based status updates (`/now`) and markdown blog posts with RSS/Atom-friendly routing.
- **Microservices & API Blueprints**:
  - `/api`: Client IP lookup, DNS utilities, QR code generator, and system helpers.
  - `/spotify`: Real-time / recent Spotify listening activity.
  - `/podcast`: Podcast episode catalog and feed aggregation.
  - `/sol`: Solana blockchain interactions and token integrations.
  - `/.well-known`: Security policies, WebFinger, and ACME challenge support.
- **Progressive Web App (PWA)**:
  - Offline asset caching with Service Worker (`/pwa/sw.js`) and web app manifest.

---

## Tech Stack

- **Runtime**: Python 3.13+
- **Framework**: Flask, Jinja2, Gunicorn
- **Package Management**: [`uv`](https://github.com/astral-sh/uv)
- **Styling**: Bootstrap 5, custom CSS overrides (`resume-custom.css`, `resume-print.css`), Bootstrap Studio (`.bsdesign`)
- **PDF Compilation**: Headless Chromium (isolated in Docker build stage)
- **Linting & Code Quality**: Ruff, pre-commit

---

## Project Structure

```text
├── blueprints/              # Modular Flask route blueprints
│   ├── acme.py              # ACME TLS verification routes
│   ├── api.py               # Public API endpoints and utility tools
│   ├── blog.py              # Blog routing and rendering
│   ├── now.py               # "Now" status updates
│   ├── podcast.py           # Podcast pages
│   ├── sol.py               # Solana blockchain endpoints
│   ├── spotify.py           # Spotify API integration
│   └── wellknown.py         # .well-known protocol handlers
├── data/                    # JSON data sources and compiled static assets
│   ├── resume.json          # Master resume configuration
│   ├── sites.json           # Directory of personal sites and projects
│   ├── tools.json           # Self-hosted / recommended software catalogue
│   ├── resume.pdf           # Generated standard resume PDF
│   └── resume_support.pdf   # Generated technical support resume PDF
├── templates/               # Jinja2 HTML templates and static assets
│   ├── assets/              # CSS stylesheets, JavaScript, fonts, and images
│   │   └── css/
│   │       ├── resume-custom.css  # Responsive & dark theme resume stylesheet
│   │       └── resume-print.css   # 1-page A4 print layout stylesheet
│   └── resume.html          # Dynamic resume template
├── pwa/                     # Progressive Web App assets & service worker
├── Dockerfile               # Multi-stage Docker build
├── main.py                  # Production entrypoint (Gunicorn runner)
├── server.py                # Core Flask application and routing
├── tools.py                 # Utility helpers, PDF builder, and CLI runner
└── pyproject.toml           # Dependencies and project metadata
```

---

## Getting Started

### Prerequisites

- [Python 3.13+](https://www.python.org/)
- [`uv`](https://docs.astral.sh/uv/) package manager
- Optional (for local PDF rebuilding): `chromium` / `google-chrome`

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Nathanwoodburn/Nathanwoodburn.github.io.git
   cd Nathanwoodburn.github.io
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Configure environment variables** (optional):
   ```bash
   cp .env.example .env  # configure any API keys if required
   ```

4. **Run the development server**:
   ```bash
   uv run python3 server.py
   ```
   The site will be available at `http://127.0.0.1:5000`.

---

## Resume Management & PDF Compilation

Resume data is edited in [`data/resume.json`](data/resume.json).

To compile the latest resume changes into standard and support PDFs manually:

```bash
uv run python3 tools.py --build-resume
```

This compiles:
- `data/resume.pdf` (Standard 1-page A4 format)
- `data/resume_support.pdf` (Technical Support tailored 1-page A4 format)

---

## Docker Deployment

The application uses a multi-stage Docker build that isolates Chromium to a build stage, keeping the final runtime image lightweight (~185 MB):

1. **Build the container**:
   ```bash
   docker build -t nathanwoodburn-site .
   ```

2. **Run the container**:
   ```bash
   docker run -d -p 5000:5000 --name nathanwoodburn-site nathanwoodburn-site
   ```

---

## Code Quality & Linting

Format and lint using Ruff:

```bash
uv run ruff check .
uv run ruff format --check .
```

---

## License

This project is open-source under the terms in [LICENSE.txt](LICENSE.txt).
