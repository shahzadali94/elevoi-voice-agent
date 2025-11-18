# 🚀 Deployment Guide - Voice Agent POC

## What We've Created

✅ Complete LiveKit voice agent codebase
✅ Dockerfile for easy deployment
✅ Git repository initialized
✅ Ready to deploy to Railway (free tier)

## Step-by-Step Deployment (30 minutes)

### Step 1: Sign Up for Free Tier Services (10 minutes)

#### 1.1 LiveKit Cloud
```
1. Go to: https://cloud.livekit.io/
2. Click "Start for Free"
3. Create account (Google/GitHub)
4. Create new project: "elevoi-voice"
5. Go to Settings → API Keys
6. Copy:
   - LIVEKIT_URL (wss://elevoi-voice-xxxxxxx.livekit.cloud)
   - LIVEKIT_API_KEY
   - LIVEKIT_API_SECRET
```

**Free Tier:** 10,000 participant minutes/month

#### 1.2 Deepgram
```
1. Go to: https://console.deepgram.com/
2. Sign up (Google/GitHub)
3. Go to API Keys
4. Create new key: "elevoi-voice-agent"
5. Copy DEEPGRAM_API_KEY
```

**Free Tier:** 200 hours of transcription/month

#### 1.3 OpenAI (you may already have)
```
1. Go to: https://platform.openai.com/api-keys
2. Create new secret key
3. Copy OPENAI_API_KEY
```

---

### Step 2: Deploy to Railway (10 minutes)

#### 2.1 Create Railway Account
```
1. Go to: https://railway.app/
2. Click "Start a New Project"
3. Sign in with GitHub
```

#### 2.2 Create GitHub Repository
```bash
cd ~/Desktop/elevoi-voice-agent

# Create repo on GitHub first, then:
git remote add origin https://github.com/YOUR_USERNAME/elevoi-voice-agent.git
git push -u origin main
```

#### 2.3 Deploy from GitHub
```
1. In Railway dashboard: "New Project"
2. Select "Deploy from GitHub repo"
3. Choose "elevoi-voice-agent"
4. Railway will auto-detect Dockerfile
```

#### 2.4 Add Environment Variables
In Railway dashboard → Variables tab, add:

```
LIVEKIT_URL=wss://elevoi-voice-xxxxxxx.livekit.cloud
LIVEKIT_API_KEY=your-livekit-api-key
LIVEKIT_API_SECRET=your-livekit-api-secret
OPENAI_API_KEY=your-openai-key
DEEPGRAM_API_KEY=your-deepgram-key
ELEVOI_API_URL=https://elevoi.vercel.app
ELEVOI_API_KEY=your-secret-key
```

Click "Deploy"

---

### Step 3: Update Vercel Integration (10 minutes)

#### 3.1 Install LiveKit SDK in Elevoi
```bash
cd ~/Desktop/elevoi
npm install livekit-server-sdk
```

#### 3.2 Add Environment Variables to Vercel
```bash
vercel env add LIVEKIT_URL
# Paste: wss://elevoi-voice-xxxxxxx.livekit.cloud

vercel env add LIVEKIT_API_KEY
# Paste your key

vercel env add LIVEKIT_API_SECRET
# Paste your secret
```

#### 3.3 Update Voice Webhook

Create new file: `/Users/shahzad/Desktop/elevoi/src/app/api/webhooks/voice-livekit/route.ts`

```typescript
import { NextRequest, NextResponse } from "next/server"
import { db } from "@/lib/db"
import { AccessToken } from "livekit-server-sdk"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()
    const callSid = formData.get("CallSid") as string
    const from = formData.get("From") as string
    const to = formData.get("To") as string

    console.log(`📞 LiveKit call: ${callSid} from ${from}`)

    // Get AI config
    const aiConfig = await db.aIAssistantConfig.findFirst({
      where: {
        twilioPhoneNumber: to,
        isEnabled: true,
      },
      include: {
        business: {
          select: {
            id: true,
            name: true,
          },
        },
      },
    })

    if (!aiConfig) {
      console.error("No AI config for:", to)
      const errorTwiml = `<?xml version="1.0" encoding="UTF-8"?>
        <Response>
          <Say>This number is not configured.</Say>
          <Hangup/>
        </Response>`
      return new NextResponse(errorTwiml, {
        headers: { "Content-Type": "text/xml" },
      })
    }

    // Create LiveKit room
    const roomName = `call-${callSid}`

    // Generate LiveKit token
    const token = new AccessToken(
      process.env.LIVEKIT_API_KEY!,
      process.env.LIVEKIT_API_SECRET!,
      {
        identity: `caller-${from.replace(/\+/g, "")}`,
        metadata: JSON.stringify({
          businessId: aiConfig.business.id,
          businessName: aiConfig.business.name,
          callSid: callSid,
        }),
      }
    )

    token.addGrant({
      roomJoin: true,
      room: roomName,
    })

    const jwt = token.toJwt()

    // Create TwiML to connect to LiveKit
    const twiml = `<?xml version="1.0" encoding="UTF-8"?>
      <Response>
        <Connect>
          <Stream url="${process.env.LIVEKIT_URL}">
            <Parameter name="token" value="${jwt}" />
            <Parameter name="room" value="${roomName}" />
          </Stream>
        </Connect>
      </Response>`

    console.log(`✅ LiveKit room created: ${roomName}`)

    return new NextResponse(twiml, {
      status: 200,
      headers: { "Content-Type": "text/xml" },
    })
  } catch (error: any) {
    console.error("LiveKit webhook error:", error)
    const errorTwiml = `<?xml version="1.0" encoding="UTF-8"?>
      <Response>
        <Say>Technical difficulties. Please try again.</Say>
        <Hangup/>
      </Response>`
    return new NextResponse(errorTwiml, {
      headers: { "Content-Type": "text/xml" },
    })
  }
}

export async function GET() {
  return NextResponse.json({
    message: "LiveKit voice webhook active",
    status: "ready",
  })
}
```

#### 3.4 Deploy to Vercel
```bash
git add -A
git commit -m "feat: Add LiveKit voice webhook"
git push origin main
vercel --prod
```

---

### Step 4: Update Twilio Webhook (2 minutes)

Go to Twilio Console → Phone Numbers → Your Number

Change webhook URL to:
```
https://elevoi.vercel.app/api/webhooks/voice-livekit
```

---

### Step 5: Test! 🎉

Call your Twilio number: **(289) 813-7861**

You should hear:
- Natural voice (not robotic)
- Fast responses (<800ms)
- Intelligent conversation
- Successful booking

---

## Troubleshooting

### Agent Not Connecting

**Check Railway Logs:**
```
railway logs
```

Look for:
- ✅ `Starting voice agent for room: call-xxxxx`
- ✅ `Participant joined: caller-xxxxx`
- ❌ Connection errors

**Fix:** Verify LiveKit credentials in Railway

### Poor Voice Quality

**Check Latency in Logs:**
```
railway logs | grep latency
```

**If >1000ms:**
- Verify Deepgram API key
- Check OpenAI API quota
- Restart Railway service

### Booking Not Working

**Test API Endpoint:**
```bash
curl https://elevoi.vercel.app/api/appointments/availability?date=2025-12-01&time=14:00
```

**Fix:** Add ELEVOI_API_KEY to Railway

---

## Cost Monitor

### Current Usage (Free Tier)

| Service | Free Tier | Current | Status |
|---------|-----------|---------|--------|
| LiveKit | 10K mins | 0 | ✅ |
| Deepgram | 200 hours | 0 | ✅ |
| OpenAI | Pay-as-go | $0 | ✅ |
| Railway | $5 credit | $0 | ✅ |

**Monthly Cost:** $0-30 (depending on OpenAI usage)

---

## Next Optimizations

Once POC is validated:

1. **Replace OpenAI with Groq** (free, faster)
2. **Add Piper TTS** (open source, $0)
3. **Move to cheap VPS** ($5/month for everything)

**Target:** <$10/month at scale

---

## Support

If you encounter issues:
1. Check Railway logs
2. Verify environment variables
3. Test each endpoint individually
4. Open GitHub issue

---

## Success Checklist

- [ ] LiveKit account created
- [ ] Deepgram account created
- [ ] Railway deployed successfully
- [ ] Environment variables added
- [ ] Vercel webhook updated
- [ ] Twilio webhook pointed to new endpoint
- [ ] Test call successful
- [ ] Booking works end-to-end

---

🎉 **Once all checked, you have a production-ready open-source voice AI!**
