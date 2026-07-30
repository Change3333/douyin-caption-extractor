<p align="center">
  <img src="assets/hero-v2.png" alt="Douyin Caption Extractor" width="100%">
</p>

<h1 align="center">Douyin Caption Extractor</h1>

<p align="center">
  <a href="README.md">简体中文</a> · English
</p>

<p align="center">
  Paste a Douyin video or photo-post share link, extract the publisher-written description, and copy it in one click.
</p>

> [!TIP]
> **No installation required:** [Open the live HTTPS demo](https://change333.dpdns.org/). The public demo is intended for personal, low-concurrency use.

> [!NOTE]
> This project extracts the text description entered by the post publisher. It does not transcribe speech, perform OCR, or download the video.

If this project saves you time, consider giving it a **Star** so more people can discover it.

## Features

- Detects a Douyin URL inside the complete share text
- Supports common `v.douyin.com` short links
- Works with video and photo posts
- Uses network responses, server-rendered data, page elements, and the title as layered extraction methods
- Provides a mobile-friendly self-hosted web interface
- Copies reliably on HTTPS, localhost, and local-network HTTP pages

## Interface

<p align="center">
  <img src="assets/demo-ui.png" alt="Douyin Caption Extractor result interface" width="720">
</p>

## Quick start

Requirements:

- Python 3.10+
- Chromium
- Xvfb when running the visible browser on a headless Linux server

### Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
python douyin_desc.py
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
xvfb-run -a python douyin_desc.py
```

Then open `http://127.0.0.1:5000`.

For a Linux server, run the app behind Nginx with HTTPS and use a process manager. The [Chinese README](README.md#linux-服务器部署) contains a Gunicorn and Xvfb example.

## Troubleshooting

### Extraction occasionally fails

Douyin page structure, risk controls, or login requirements may change. Try again later, open the short link in a regular browser and submit the resulting long URL, and verify that Chromium starts correctly on the server.

### The copy button does not work

The Clipboard API normally requires HTTPS or localhost. This project includes a fallback for local-network HTTP pages, but HTTPS remains recommended for public deployments.

## Contributing

Bug reports, feature ideas, documentation improvements, and pull requests are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) before contributing.

Use this project only for content you are authorized to access. Follow applicable laws, platform terms, copyright rules, and reasonable request-rate limits.

## License

[MIT](LICENSE) © Contributors
