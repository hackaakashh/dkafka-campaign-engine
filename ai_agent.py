"""
AI Agent — powered by Claude (Anthropic).
Handles: email generation, reply classification, human-like reply drafting,
and farewell generation.
"""

import json
import anthropic
from config import ANTHROPIC_API_KEY, FROM_NAME, CAMPAIGN_NAME, CAMPAIGN_GOAL, CAMPAIGN_TONE, CAMPAIGN_AUDIENCE

STAGE_CONTEXT = {
    "TOFU":   "Top of funnel — introduce yourself warmly, offer genuine value, NO hard sell",
    "MOFU":   "Middle of funnel — they opened your email, show deeper insight, soft call to action",
    "BOFU":   "Bottom of funnel — they clicked a link, they are clearly interested, clearer CTA, address hesitation",
    "RESEND": "They did not open your first email. New subject line, more personal opening, try a different angle",
    "SUNSET": "7 days, no engagement. Wish them well. Leave door open. No guilt, no pressure.",
}


class AIAgent:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # ─────────────────────────────────────────────────────────────────────
    # 1. Generate campaign email
    # ─────────────────────────────────────────────────────────────────────
    def generate_email(self, subscriber_name: str, stage: str, day: int,
                       extra_hint: str = "") -> tuple[str, str, str]:
        """
        Returns (subject, html_body, text_body).
        Inserts [UNSUBSCRIBE_LINK] placeholder — mailer replaces with real URL.
        """
        prompt = f"""You are {FROM_NAME} writing a personal email for this campaign.

Campaign: {CAMPAIGN_NAME}
Goal: {CAMPAIGN_GOAL}
Audience: {CAMPAIGN_AUDIENCE}
Tone: {CAMPAIGN_TONE}
Day: {day} of 7
Stage: {stage} — {STAGE_CONTEXT.get(stage, '')}
Subscriber's name: {subscriber_name}
{f'Extra instruction: {extra_hint}' if extra_hint else ''}

Write like a real person who genuinely cares — NOT a marketing template.
Keep it SHORT: 3 short paragraphs max. End by signing as {FROM_NAME}.

HARD RULES:
- Subject: under 50 characters, no spam trigger words (FREE, URGENT, !!!, CLICK NOW)
- Include exactly [UNSUBSCRIBE_LINK] once in both html_body and text_body
- HTML: use only simple <p> and <br> tags, no complex CSS
- Plain text: just text, no HTML tags

Respond ONLY with valid JSON. No markdown fences. No explanation:
{{"subject": "...", "html_body": "<p>...</p>", "text_body": "..."}}"""

        data = self._call_json(prompt, max_tokens=900)
        return data["subject"], data["html_body"], data["text_body"]

    # ─────────────────────────────────────────────────────────────────────
    # 2. Classify reply sentiment
    # ─────────────────────────────────────────────────────────────────────
    def classify_reply(self, reply_text: str) -> str:
        """Returns exactly: 'positive', 'negative', or 'neutral'"""
        prompt = f"""Classify this email reply. Reply with ONE word only.

Campaign context: {CAMPAIGN_GOAL}
Reply: "{reply_text[:600]}"

positive  = interested, asking questions, wants more info, warm response
negative  = not interested, stop emailing me, unsubscribe, rude or dismissive
neutral   = auto-reply, out of office, generic acknowledgement, unclear

Reply with EXACTLY one word: positive  OR  negative  OR  neutral"""

        result = self._call_raw(prompt, max_tokens=5).strip().lower()
        if result not in ("positive", "negative", "neutral"):
            result = "neutral"
        print(f"[AI CLASSIFY] '{reply_text[:60]}...' → {result}")
        return result

    # ─────────────────────────────────────────────────────────────────────
    # 3. Generate reply to positive subscriber
    # ─────────────────────────────────────────────────────────────────────
    def generate_reply(self, subscriber_name: str, their_reply: str,
                       history: list) -> tuple[str, str]:
        """
        Returns (html_reply, text_reply).
        References what the subscriber actually said — never sounds robotic.
        """
        history_str = ""
        if history:
            recent = history[-4:]
            history_str = "\n\nConversation so far:\n" + "\n".join(
                f"  {h['role'].upper()}: {h['content'][:200]}" for h in recent
            )

        prompt = f"""You are {FROM_NAME} replying to a subscriber named {subscriber_name}.

Their message: "{their_reply}"
{history_str}

Write a warm, personal reply. REFERENCE what they actually said — do not ignore it.
3-4 sentences max. Sound like a real human, not a system.
Sign off as {FROM_NAME}.

Respond ONLY with valid JSON. No markdown fences:
{{"html_body": "<p>...</p>", "text_body": "..."}}"""

        data = self._call_json(prompt, max_tokens=600)
        return data["html_body"], data["text_body"]

    # ─────────────────────────────────────────────────────────────────────
    # 4. Generate one farewell for negative reply
    # ─────────────────────────────────────────────────────────────────────
    def generate_farewell(self, subscriber_name: str,
                          their_reply: str) -> tuple[str, str, str]:
        """
        Returns (subject, html_body, text_body).
        This email is sent ONCE, then the subscriber is DO_NOT_CONTACT forever.
        """
        prompt = f"""You are {FROM_NAME}. A subscriber named {subscriber_name} does not want emails anymore.

Their message: "{their_reply[:400]}"

Write ONE short gracious farewell. Warm, not guilt-tripping.
This is the LAST email they will ever get. Make it dignified and kind.
2-3 sentences max.

Respond ONLY with valid JSON. No markdown fences:
{{"subject": "...", "html_body": "<p>...</p>", "text_body": "..."}}"""

        data = self._call_json(prompt, max_tokens=400)
        return data["subject"], data["html_body"], data["text_body"]

    # ─────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────
    def _call_json(self, prompt: str, max_tokens: int) -> dict:
        raw = self._call_raw(prompt, max_tokens)
        clean = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)

    def _call_raw(self, prompt: str, max_tokens: int) -> str:
        response = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
