# Omni-Agent — Automated Viral Animal Facts Video Engine

Fully automated pipeline that generates, composes, and posts short-form animal fact videos to YouTube Shorts, TikTok, and Instagram on a schedule. No manual intervention required.

## How It Works

```
Schedule (every 6h)
    │
    ▼
1. Pick random animal (AI-generated, unlimited variety)
    │
    ▼
2. Generate 3-layer viral fact
   ├── short_fact   → scroll-stopping 1-liner for video overlay
   ├── description  → 3-5 sentence expansion for captions
   ├── hashtags     → mix of broad + specific
   └── emotion      → rotates: joy, awe, empathy, curiosity, power
    │
    ▼
3. Build hyperrealistic Sora 2 prompt
   ├── Failproof habitat (80+ animals hardcoded to real habitats)
   ├── Photographer-style: species details, lighting, lens, DOF
   └── Negative phrasing to prevent hallucinations
    │
    ▼
4. Generate video via Sora 2 (Kie.ai API)
   ├── Background task saved to PostgreSQL
   ├── Polled every 30 seconds until complete (~2-5 min)
   └── Fallback: Pexels stock footage if Sora fails
    │
    ▼
5. Compose final video
   ├── Download raw video
   ├── Convert to 9:16 portrait (1080x1920)
   ├── Add white bar at top (250px) with fact text
   └── Subtle @howanimalslove watermark
    │
    ▼
6. Post to social platforms via Blotato API
   ├── YouTube Shorts → "Did You Know This About {animal}? 🐾 #shorts"
   ├── TikTok         → short fact + hashtags (150 char friendly)
   └── Instagram      → full description + CTA + hashtags
```

## Architecture

```
Omni-Agent/
├── app.py                          # Flask API + endpoints
├── core/
│   ├── scheduler.py                # APScheduler (6h interval + 30s task polling)
│   ├── async_workflow_wrapper.py   # Handles async Sora generation with DB tracking
│   ├── video_task_processor.py     # Background processor: poll → compose → post
│   ├── pexels_client.py            # Pexels fallback (wildlife-only filtering)
│   ├── alerter.py                  # Telegram alerts on failures
│   └── memory.py                   # PostgreSQL models (PendingVideoTask)
├── workflows/
│   └── animal_facts.py             # Main workflow: fact gen, Sora, compose, post
├── utils/
│   ├── sora_prompt_builder.py      # Hyperrealistic prompt with HABITAT_MAP
│   └── video_composer.py           # FFmpeg/moviepy composition (white bar + text)
├── api/
│   └── model_router.py             # AI via OpenRouter (Gemini Flash default)
└── assets/
    └── fonts/Inter.ttf             # Bundled font for cross-platform rendering
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `KIE_API_KEY` | Yes | Kie.ai API key for Sora 2 video generation |
| `OPENROUTER_API_KEY` | Yes | OpenRouter API key for AI fact generation |
| `BLOTATO_API_KEY` | Yes | Blotato API key for social media posting |
| `PEXELS_API_KEY` | Recommended | Pexels API key (fallback video source) |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `TELEGRAM_BOT_TOKEN` | Recommended | Telegram bot for failure alerts |
| `TELEGRAM_ALERT_USER_ID` | Recommended | Telegram user ID for alerts |
| `RAILWAY_PUBLIC_DOMAIN` | Auto-set | Railway sets this; used for serving composed videos |

## Error Handling & Reliability

- **Sora fails**: Retries 3 times with exponential backoff (30s, 60s, 120s), then falls back to Pexels stock footage
- **AI fact generation fails**: Falls back to simple single-line fact generation, then hardcoded fallback
- **Video composition fails**: Posts raw video without overlay (still posts)
- **Blotato posting fails**: Video is saved, error logged, Telegram alert sent
- **Task stuck >15 min**: Moved to dead letter queue, Telegram alert sent
- **Railway redeploy**: Scheduler auto-restarts on boot, pending DB tasks resume processing

## API Endpoints

### Production
- `POST /api/animal-facts/run` — Run full workflow (fact → video → compose → post)
- `POST /api/animal-facts/preview` — Preview fact + prompt without generating video
- `POST /api/scheduler/animal-facts` — Configure schedule (interval_hours, enabled)
- `GET /api/scheduler/schedules` — View active schedules

### Debug / Testing
- `POST /api/animal-facts/test-overlay` — Test composition with any video URL
- `GET /api/debug/poll-kie/<task_id>` — Direct Kie.ai task status check
- `POST /api/debug/process-tasks` — Manually trigger background task processing
- `POST /api/animal-facts/search-pexels` — Test Pexels search for an animal

## Video Spec

- **Resolution**: 1080x1920 (9:16 portrait)
- **Bar height**: 250px white bar at top
- **Font**: Inter Bold, 36-60px (auto-sized to fit)
- **Watermark**: @howanimalslove, light gray (#8c8c8c), 26-30px
- **Content**: Real wildlife footage only — no puppets, cartoons, or animations

## Deployed On

Railway at `web-production-770b9.up.railway.app`

## License

MIT
