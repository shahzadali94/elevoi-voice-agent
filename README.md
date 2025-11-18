# Elevoi Voice Agent - Open Source POC

AI-powered voice agent for booking appointments using LiveKit + open source models.

## Architecture

```
Phone Call → Twilio → Vercel → LiveKit Cloud → Voice Agent (Railway)
```

## Features

- ✅ Real-time voice conversations
- ✅ Natural language understanding
- ✅ Appointment booking & availability checking
- ✅ Sub-second latency
- ✅ Open source & cost-effective

## Tech Stack

- **Media Server**: LiveKit Cloud (free tier)
- **STT**: Deepgram (free tier)
- **LLM**: OpenAI GPT-4o-mini (affordable)
- **TTS**: OpenAI TTS
- **Deployment**: Railway (free tier)

## Setup Instructions

### 1. Sign up for Free Tier Services

#### LiveKit Cloud
1. Go to https://cloud.livekit.io
2. Create account
3. Create project
4. Get API Key and Secret

#### Deepgram
1. Go to https://deepgram.com
2. Create account
3. Get API key (200 hours free/month)

### 2. Clone and Setup

```bash
git clone <repo-url>
cd elevoi-voice-agent

# Create .env file
cp .env.example .env

# Edit .env with your keys
nano .env
```

### 3. Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app)

**Manual Deploy:**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Create new project
railway init

# Add environment variables
railway variables set LIVEKIT_URL=wss://your-project.livekit.cloud
railway variables set LIVEKIT_API_KEY=your-key
railway variables set LIVEKIT_API_SECRET=your-secret
railway variables set OPENAI_API_KEY=your-key
railway variables set DEEPGRAM_API_KEY=your-key
railway variables set ELEVOI_API_URL=https://elevoi.vercel.app
railway variables set ELEVOI_API_KEY=your-key

# Deploy
railway up
```

### 4. Update Vercel Webhook

In your Elevoi app, update the voice webhook to use LiveKit.

See `INTEGRATION.md` for complete integration guide.

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export LIVEKIT_URL=wss://your-project.livekit.cloud
export LIVEKIT_API_KEY=your-key
export LIVEKIT_API_SECRET=your-secret
export OPENAI_API_KEY=your-key
export DEEPGRAM_API_KEY=your-key

# Run agent
python agent.py dev
```

## Cost Breakdown (1000 minutes/month)

| Service | Cost |
|---------|------|
| LiveKit Cloud | $0 (free tier) |
| Deepgram STT | $0 (free tier) |
| OpenAI GPT-4o-mini | ~$15 |
| OpenAI TTS | ~$15 |
| Railway | $0 (free tier) |
| **Total** | **~$30/month** |

Compare to current Twilio+GPT-4 setup: **$100/month**
**Savings: 70%**

## Future Optimizations

To reduce costs further:
- Replace OpenAI LLM with Groq (free tier)
- Replace OpenAI TTS with Piper (open source)
- Self-host on cheap VPS ($5/month)

**Target cost at scale:** <$10/month

## Troubleshooting

**Agent not connecting:**
- Check LiveKit credentials
- Verify Railway deployment logs: `railway logs`

**Poor voice quality:**
- Check latency in logs
- Verify Deepgram API quota

**Booking not working:**
- Check Elevoi API URL and key
- Verify network connectivity

## Support

Open an issue on GitHub for help.

## License

MIT
