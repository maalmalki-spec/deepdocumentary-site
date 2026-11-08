# Deep Documentary — Instagram Reels review pipeline

This workflow is **review-only**. It never posts to Instagram, never asks for account credentials, and never changes the live website.

## How to use
1. In GitHub Actions, open **Generate Instagram Reel Review** and choose **Run workflow** with an article path such as `articles/apollo-11.html`.
2. A push modifying `articles/*.html` also triggers generation on the branch where this workflow is enabled.
3. Download the `instagram-reels-review-*` artifact from the workflow run. It contains `review.mp4` and `review.json`.
4. Review the wording, visuals, copyright and factual accuracy before any manual posting.

## Limitations
This first implementation generates a **silent 1080×1920, 24fps, 25-second storyboard**, not a narrated documentary. It uses article text and a simple black/gold design; Arabic shaping depends on Pillow's RAQM support. A polished version needs licensed footage, Arabic TTS, subtitles, transitions and a human approval gate. No automatic publishing is implemented. GitHub Actions minutes and artifact storage are subject to the repository plan's quotas.
