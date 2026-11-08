# Instagram Reels — approved language specification

- Voiceover: **English only**, natural documentary narration (deep, clear, cinematic).
- Subtitles: **Arabic only**, burned into the video, synchronized to the spoken English.
- Video: 1080 × 1920 (9:16), black/gold Deep Documentary identity.
- Publishing: **manual approval required**. Never automatically publish to Instagram.
- Budget: favor free/local tools, no external editor watermark.
- Editorial: verify the English narration and Arabic translation against the article. Do not translate Arabic paragraphs by simply labeling them English.
- Timing: subtitle cues must match spoken segments; use voice/audio duration or timestamps, not arbitrary fixed slide timing.
- Accessibility: keep Arabic subtitles inside mobile-safe margins and readable against moving footage.

## Implementation gate
The existing generator in `scripts/generate_reel_review.py` produces silent storyboard previews only. It does **not** yet implement English narration or Arabic subtitles. Do not mark voiceover/subtitles as complete until an end-to-end generated MP4 is checked for both tracks and Arabic text rendering.
