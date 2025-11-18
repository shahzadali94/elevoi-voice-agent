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

    def __init__(self, business_id: str):
        self.business_id = business_id
        self.elevoi_api_url = os.getenv("ELEVOI_API_URL", "https://elevoi.vercel.app")
        self.elevoi_api_key = os.getenv("ELEVOI_API_KEY", "")

    async def check_availability(
        self,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        duration_minutes: Annotated[int, "Duration in minutes (default 30)"] = 30
    ) -> str:
        """Check available appointment slots for a given date"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.elevoi_api_url}/api/voice-agent/availability",
                    params={
                        "businessId": self.business_id,
                        "date": date,
                        "duration": duration_minutes
                    },
                    headers={"Authorization": f"Bearer {self.elevoi_api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    if data.get("available") and data.get("slots"):
                        slots = data["slots"][:5]  # Show first 5 slots
                        slot_times = []
                        for slot in slots:
                            start_time = slot.get("startTime", "")
                            # Extract time from ISO string (e.g., "14:00" from "2024-01-01T14:00:00")
                            if "T" in start_time:
                                time_part = start_time.split("T")[1].split(":")[0:2]
                                time_str = ":".join(time_part)
                                slot_times.append(time_str)

                        if slot_times:
                            times_str = ", ".join(slot_times[:3])
                            return f"Yes, we have availability on {date}. Some available times are: {times_str}. What time works best for you?"
                        else:
                            return f"We have {len(slots)} available slots on {date}. What time would you prefer?"
                    else:
                        return f"I'm sorry, we don't have any availability on {date}. Would you like to try a different date?"
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
        customer_name: Annotated[str, "Customer's full name"],
        customer_phone: Annotated[str, "Customer's phone number"],
        duration_minutes: Annotated[int, "Duration in minutes (default 30)"] = 30
    ) -> str:
        """Book an appointment for the customer"""
        try:
            from datetime import datetime, timedelta

            # Parse date and time
            start_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
            end_datetime = start_datetime + timedelta(minutes=duration_minutes)

            # Format as ISO strings
            start_time_iso = start_datetime.isoformat()
            end_time_iso = end_datetime.isoformat()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.elevoi_api_url}/api/voice-agent/book",
                    json={
                        "businessId": self.business_id,
                        "customerName": customer_name,
                        "customerPhone": customer_phone,
                        "service": service,
                        "startTime": start_time_iso,
                        "endTime": end_time_iso,
                        "notes": "Booked via AI voice agent"
                    },
                    headers={"Authorization": f"Bearer {self.elevoi_api_key}"},
                    timeout=10.0
                )

                if response.status_code == 201:
                    data = response.json()
                    return f"Perfect! Your {service} appointment is confirmed for {date} at {time}. You'll receive a confirmation text message shortly. Is there anything else I can help you with?"
                else:
                    error_data = response.json()
                    error_msg = error_data.get("error", "Please try again.")
                    if "already booked" in error_msg.lower():
                        return f"I apologize, but that time slot was just booked by someone else. Let me check other available times for you."
                    return f"I couldn't book that appointment. {error_msg}"
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            return "I'm having trouble booking the appointment right now. Let me transfer you to our staff."


async def entrypoint(ctx: JobContext):
    """Main entry point for the voice agent"""
    logger.info(f"Starting voice agent for room: {ctx.room.name}")

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

    if not business_id:
        logger.error("⚠️ No business_id in room metadata! Cannot initialize booking agent.")
        return

    logger.info(f"Agent serving business: {business_name} (ID: {business_id})")

    # Initialize booking helper with business_id
    booking_agent = AppointmentBookingAgent(business_id)

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
