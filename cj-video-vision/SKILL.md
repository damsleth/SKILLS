---
name: cj-video-vision
description: Watch and analyze videos via the claude-video-vision MCP server — frame extraction, scene/silence/motion analysis, and audio transcription for local files and YouTube URLs. Use when the user mentions a video file (.mp4, .mov, .avi, .mkv, .webm), pastes a YouTube URL, asks to watch/analyze/review/summarize a video, or references video content in conversation. Also use to install or configure the video-vision MCP itself.
---

# cj-video-vision

## Overview

[claude-video-vision](https://github.com/damsleth/claude-video-vision) is an MCP server
that gives agents video perception: ffmpeg-based structural analysis, frame extraction
at variable FPS/resolution, and audio transcription (Whisper or YouTube captions).
It handles local video files and YouTube URLs (downloaded via `yt-dlp`).

The server exposes six tools, all prefixed `mcp__claude-video-vision__`:

- `video_info` — metadata (duration, resolution, audio presence) without processing
- `video_analyze` — structural analysis via ffmpeg filters (scene changes, silence, motion, freeze, blur, exposure, loudness, black intervals) + transcription
- `video_watch` — extract frames + process audio; supports per-segment FPS/resolution
- `video_detail` — drill into specific segments; extract many frames, view few
- `video_configure` — change settings (backend, resolution, enable_index, …)
- `video_setup` — check/install dependencies (ffmpeg, yt-dlp, whisper)

## Boot

Check that the MCP tools are reachable (e.g. via ToolSearch for `video_info`). If the
server isn't connected, register it and tell the user to restart the session:

```bash
claude mcp add --scope user claude-video-vision -- npx -y claude-video-vision@latest
```

On first use, run `video_setup` to verify dependencies (ffmpeg required; yt-dlp for
YouTube; a whisper backend for transcription). Config and frame cache honor
`XDG_CONFIG_HOME` as of v1.3.x.

## Workflow

**IMPORTANT: Follow these steps in order. Do NOT skip step 2.**

1. Always start with `video_info` to get duration, resolution, and audio presence.
   If the user gives a YouTube URL, pass the URL directly as `path`. The server
   downloads it with `yt-dlp`, prefers YouTube subtitles/auto-captions for
   transcription, and falls back to the configured audio backend only when captions
   are missing, empty, or suspiciously incomplete.

2. **REQUIRED for videos > 30s:** Call `video_analyze` BEFORE extracting any frames.
   This is NOT optional — it gives you structural data to make smart extraction
   decisions. Select filters relevant to the user's question:

   | User intent | Filters to select |
   |---|---|
   | "What happens in this video?" | scene_changes, silence, transcription |
   | "Find the scene transitions" | scene_changes, black_intervals |
   | "Are there frozen/stuck parts?" | freeze, blur |
   | "Is this a talking head or action?" | motion |
   | "When does the music start?" | silence, loudness |
   | "Analyze the lighting" | exposure |
   | "Summarize this lecture" | transcription, scene_changes, silence |
   | General / unclear intent | scene_changes, silence, transcription |

   Always include `transcription: true` when the video has audio — the transcription
   tells you WHERE to look visually.

3. Use the analysis results and transcription to plan frame extraction:
   - Low FPS (0.1-0.5) for static or predictable segments
   - Higher FPS (1-3) only around scene changes, motion peaks, or moments
     referenced in speech ("look at this", "as you can see", "let me show you")
   - Never exceed the minimum FPS needed for the task
   - Prefer fewer segments at lower FPS — you can always drill deeper

4. Call `video_watch` to extract frames:
   - **Short videos (< 2 minutes):** use `fps: "auto"` without `view_sample` — short
     videos need full coverage to avoid missing brief moments
   - **Long videos (> 2 minutes):** use `segments` based on analysis data with
     variable FPS, and `view_sample` to limit initial frame count

5. Use `video_detail` to drill into specific moments:
   - Start with 3-5 second windows around points of interest
   - Use `view_sample: 3` to preview (first, middle, last frame)
   - Then request specific timestamps with `view` if you need more detail
   - Treat frame viewing like a binary search — never view all extracted frames at once

6. On follow-up questions about the same video, consult the manifest already in
   context. Do not re-extract or re-view frames you already have at the same
   resolution.

## Parameter Guide

- **fps:** `"auto"` for general overview. The video's original fps (from `video_info`)
  for frame-by-frame detail. 5-10 for specific short moments. 0.1-0.5 for long videos.
- **resolution:** 256-512 for quick scans. 512-768 for normal analysis. 1024+ when
  reading on-screen text or fine details.
- **segments:** Use when you have analysis data. Each segment can have its own fps
  and resolution. Overrides global fps/start_time/end_time.
- **view_sample:** Returns N evenly spaced frames from the extracted set — use it to
  avoid flooding context with images.
- **skip_audio:** Set true when you only need visual analysis.
- **YouTube URLs:** Pass directly as `path`. Treat
  `transcription_source: "youtube_subtitles"` as stronger than
  `youtube_auto_captions`; auto-captions can have recognition errors.

## Working with Results

You receive:

- **Manifest** (when enable_index is on) — index of all cached frames by resolution
  and timestamp; use it to avoid redundant requests
- **Frames** as images — look at them to understand what happens visually
- **Audio transcription** with timestamps — read the speech content
- **Audio tags** — non-speech events (music, sounds, …)
- **Analysis data** — scene changes, silence intervals, motion levels, …

Combine all sources: the analysis and transcription tell you WHEN things happen;
the frames tell you WHAT happens.
