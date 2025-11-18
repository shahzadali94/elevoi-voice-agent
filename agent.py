"""
Elevoi Voice Agent - Open Source POC
Uses free tier services for testing
"""

import asyncio
import logging
import os
from typing import Annotated
from livekit import agents, rtc
from livekit.agents import JobContext, WorkerOptions, cli, tokenize, tts
from livekit.plugins import deepgram, openai, silero
import httpx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AppointmentBookingAgent:
    """AI Agent for booking appointments via phone"""

    def __init__(self):
        self.elevoi_api_url = os.getenv("ELEVOI_API_URL", "https://elevoi.vercel.app")
        self.elevoi_api_key = os.getenv("ELEVOI_API_KEY", "")

    async def check_availability(
        self,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        time: Annotated[str, "Time in HH:MM format (24-hour)"]
    ) -> str:
        """Check if an appointment slot is available"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.elevoi_api_url}/api/appointments/availability",
                    params={"date": date, "time": time},
                    headers={"Authorization": f"Bearer {self.elevoi_api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("available"):
                        return f"Yes, {date} at {time} is available. Would you like to book it?"
                    else:
                        alternatives = data.get("alternatives", [])
                        if alternatives:
                            alt_times = ", ".join([f"{a['time']}" for a in alternatives[:3]])
                            return f"That time is not available. How about these times: {alt_times}?"
                        return "That time is not available. Would you like to try a different time?"
                else:
                    return "I'm having trouble checking availability. Let me transfer you to our staff."
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            return "I'm having trouble checking availability right now."

    async def book_appointment(
        self,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        time: Annotated[str, "Time in HH:MM format (24-hour)"],
        service: Annotated[str, "Service name (e.g., 'Haircut', 'Massage')"],
        customer_name: Annotated[str, "Customer's full name"] = "Unknown",
        customer_phone: Annotated[str, "Customer's phone number"] = ""
    ) -> str:
        """Book an appointment for the customer"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.elevoi_api_url}/api/appointments/book",
                    json={
                        "date": date,
                        "time": time,
                        "service": service,
                        "customerName": customer_name,
                        "customerPhone": customer_phone
                    },
                    headers={"Authorization": f"Bearer {self.elevoi_api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    return f"Great! Your {service} appointment is confirmed for {date} at {time}. You'll receive a confirmation shortly."
                else:
                    error_data = response.json()
                    return f"I couldn't book that appointment. {error_data.get('error', 'Please try again.')}"
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return "I'm having trouble booking the appointment right now. Let me transfer you to our staff."


async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent"""
    logger.info(f"Starting voice agent for room: {ctx.room.name}")

    # Initialize booking helper
    booking_agent = AppointmentBookingAgent()

    # Get business context from room metadata
    room_metadata = ctx.room.metadata or "{}"
    import json
    try:
        metadata = json.loads(room_metadata)
        business_name = metadata.get("businessName", "our business")
        business_id = metadata.get("businessId")
    except:
        business_name = "our business"
        business_id = None

    logger.info(f"Agent serving business: {business_name} (ID: {business_id})")

    # Create system prompt
    initial_ctx = agents.llm.ChatContext().append(
        role="system",
        text=(
            f"You are a friendly, professional appointment booking assistant for {business_name}. "
            "Your job is to help customers book appointments quickly and efficiently. "
            "\n\nFollow these steps:"
            "\n1. Greet the customer warmly"
            "\n2. Ask what service they need"
            "\n3. Ask for their preferred date and time"
            "\n4. Check availability using the check_availability tool"
            "\n5. If available, collect their name and confirm booking using book_appointment tool"
            "\n6. If not available, suggest alternative times"
            "\n7. Confirm all details before ending the call"
            "\n\nBe conversational, friendly, and efficient. Keep responses concise."
            "\n\nImportant:"
            "\n- Always confirm details before booking"
            "\n- If you can't help, offer to transfer to a staff member"
            "\n- Use natural, conversational language"
            "\n- Don't repeat yourself"
        ),
    )

    # Initialize voice agent
    logger.info("Connecting to room...")
    await ctx.connect(auto_subscribe=agents.AutoSubscribe.AUDIO_ONLY)

    # Wait for first participant
    participant = await ctx.wait_for_participant()
    logger.info(f"Participant joined: {participant.identity}")

    # Create voice agent with plugins
    agent = agents.VoiceAssistant(
        vad=silero.VAD.load(),  # Voice Activity Detection
        stt=deepgram.STT(),     # Speech-to-Text (Deepgram free tier)
        llm=openai.LLM(         # Use OpenAI for now (will switch to Groq)
            model="gpt-4o-mini",
            temperature=0.7,
        ),
        tts=openai.TTS(          # Text-to-Speech
            voice="alloy",
        ),
        chat_ctx=initial_ctx,
    )

    # Register tools
    agent.register_function(
        "check_availability",
        booking_agent.check_availability,
    )

    agent.register_function(
        "book_appointment",
        booking_agent.book_appointment,
    )

    # Start the agent
    logger.info("Starting voice assistant...")
    agent.start(ctx.room, participant)

    # Greet the user
    await agent.say("Hello! Thank you for calling. How can I help you today?", allow_interruptions=True)

    logger.info("Voice agent is now active and listening")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
