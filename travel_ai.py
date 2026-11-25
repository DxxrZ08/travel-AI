"""
AI Travel Planner — NVIDIA NIM API Integration
Uses OpenAI-compatible endpoint to generate travel plans.
"""

import logging

from openai import OpenAI

logger = logging.getLogger(__name__)


def get_ai_client(api_key: str) -> OpenAI:
    """Create an OpenAI client pointing to NVIDIA NIM API."""
    if not api_key:
        raise ValueError("NVIDIA API key is required.")
    return OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )


SYSTEM_PROMPT = """You are an expert AI travel planner and local guide with deep knowledge of destinations worldwide.
You help users plan amazing trips by providing:

1. **Destination Recommendations** — based on their budget, interests, weather preferences, and travel style.
2. **Detailed Day-by-Day Itineraries** — with morning, afternoon, and evening breakdowns.
3. **Budget Estimation** — realistic cost breakdowns for accommodation, food, transport, activities, and miscellaneous.
4. **Hotel & Restaurant Suggestions** — with price ranges and why they're recommended.
5. **Local Tips** — cultural etiquette, safety, best time to visit, what to pack, and hidden gems.

Guidelines:
- Be specific with names of places, restaurants, and hotels (use real, well-known ones).
- Provide estimated costs in the user's preferred currency.
- Suggest both popular attractions and off-the-beaten-path experiences.
- Consider the traveler's pace — don't overpack the itinerary.
- Use emojis to make the output visually engaging (🏨 🍽️ 🚌 ✈️ 🎭 🌄 💰).
- Format output with clear markdown headers, bullet points, and tables where appropriate.
- If the user hasn't specified something, make reasonable assumptions and state them.
"""


CHATBOT_PROMPT = """You are a friendly and knowledgeable AI travel assistant chatbot.
You help users with any travel-related questions including:
- Visa requirements and travel documents
- Packing tips and travel gear recommendations
- Local customs and cultural etiquette
- Safety tips and health precautions
- Transportation options and booking tips
- Currency exchange and budgeting
- Food recommendations and dietary considerations
- Weather and best times to visit
- Language tips and useful phrases

Be conversational, helpful, and enthusiastic about travel!
Use emojis occasionally to keep it fun. Keep responses concise but informative.
"""


def build_travel_prompt(
    destination: str,
    duration: int,
    budget: str,
    travelers: int,
    interests: list,
    travel_style: str,
    start_date: str = None,
    special_requests: str = None,
    poi_hints: str = None,
) -> str:
    """Build a structured prompt for the AI travel planner."""
    interests_str = ", ".join(interests) if interests else "General sightseeing"

    prompt = f"""Plan a complete travel itinerary with the following details:

📍 **Destination:** {destination}
📅 **Duration:** {duration} days
💰 **Budget:** {budget}
👥 **Number of Travelers:** {travelers}
🎯 **Interests:** {interests_str}
🧳 **Travel Style:** {travel_style}
"""
    if start_date:
        prompt += f"📆 **Starting Date:** {start_date}\n"

    if special_requests:
        prompt += f"📝 **Special Requests:** {special_requests}\n"

    if poi_hints:
        prompt += f"""
📌 **Local Points of Interest from our Database:**
{poi_hints}
Please try to incorporate some of these verified local spots into the itinerary where relevant.
"""

    prompt += """
Please provide:
1. **Trip Overview** — A brief summary and why this destination is great for these preferences.
2. **Day-by-Day Itinerary** — Detailed plan for each day (morning, afternoon, evening).
3. **Accommodation Suggestions** — 2-3 hotel/hostel options with price ranges matching the budget.
4. **Food & Restaurant Recommendations** — Must-try local dishes and where to eat.
5. **Budget Breakdown** — Estimated costs in a table format (accommodation, food, transport, activities, total).
6. **Packing List** — Essential items based on destination and season.
7. **Pro Tips** — Local customs, safety, transportation, and money-saving tips.
"""
    return prompt


def build_budget_prompt(destination: str, duration: int, travelers: int, budget_level: str) -> str:
    """Build a prompt for budget estimation."""
    return f"""Provide a detailed budget breakdown for a trip to {destination}:

📅 Duration: {duration} days
👥 Travelers: {travelers}
💰 Budget Level: {budget_level}

Please provide a DETAILED budget breakdown in a table format with these categories:
1. ✈️ **Flights** (round trip estimate)
2. 🏨 **Accommodation** (per night × {duration} nights)
3. 🍽️ **Food & Dining** (per day × {duration} days)
4. 🚌 **Local Transport** (per day × {duration} days)
5. 🎭 **Activities & Attractions** (total estimate)
6. 🛍️ **Shopping & Souvenirs** (estimate)
7. 📱 **Miscellaneous** (SIM card, tips, emergency fund)

For each category, provide:
- Per unit cost (per day/night)
- Total cost for the trip
- Money-saving tips

End with a **Grand Total** for {travelers} traveler(s).
Use a markdown table for clarity.
"""


# Default active models on NVIDIA NIM (ultra-fast 0.7s response + fallbacks)
DEFAULT_MODELS = [
    "poolside/laguna-xs-2.1",
    "stepfun-ai/step-5-preview",
    "minimaxai/minimax-m3.1-flash",
]


def get_ai_response(client: OpenAI, prompt: str, model: str = None) -> str:
    """Get a complete (non-streamed) AI response with model fallback."""
    models_to_try = [model] if model else DEFAULT_MODELS
    last_error = None

    for m in models_to_try:
        try:
            response = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.6,
                max_tokens=4096,
                timeout=30,
            )
            msg = response.choices[0].message
            content = msg.content or getattr(msg, "reasoning_content", None)
            if content and content.strip():
                return content.strip()
            logger.warning("NVIDIA NIM returned an empty response for model %s.", m)
        except Exception as e:
            status_code = getattr(e, "status_code", None)
            logger.warning(
                "NVIDIA NIM request failed for model %s (%s, HTTP %s).",
                m,
                type(e).__name__,
                status_code or "n/a",
            )
            last_error = e
            continue

    if last_error:
        raise RuntimeError(
            "NVIDIA NIM failed for all configured models. Check the server logs for model-level errors."
        ) from last_error
    raise RuntimeError("NVIDIA NIM returned no usable response from any configured model.")


def stream_ai_response(client: OpenAI, prompt: str, model: str = None):
    """Stream the AI response for real-time display."""
    target_model = model or DEFAULT_MODELS[0]
    try:
        response = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=4096,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"\n\n❌ **Error:** {str(e)}\n\nPlease check your API key and try again."


def chat_response(client: OpenAI, messages: list, model: str = None) -> str:
    """Get a chatbot response with conversation history and model fallback."""
    models_to_try = [model] if model else DEFAULT_MODELS
    full_messages = [{"role": "system", "content": CHATBOT_PROMPT}] + messages
    last_error = None

    for m in models_to_try:
        try:
            response = client.chat.completions.create(
                model=m,
                messages=full_messages,
                temperature=0.7,
                max_tokens=1024,
                timeout=25,
            )
            msg = response.choices[0].message
            content = msg.content or getattr(msg, "reasoning_content", None)
            if content and content.strip():
                return content.strip()
        except Exception as e:
            last_error = e
            continue

    return f"Sorry, I encountered an error: {str(last_error)}. Please try again!"
