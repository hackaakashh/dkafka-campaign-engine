"""
State machine for the campaign engine.
Every subscriber moves through these states based on their behaviour —
NOT a fixed schedule.
"""

# ── All possible subscriber states ────────────────────────────────────────
ACTIVE           = "ACTIVE"           # just enrolled (Kishalay's default)
EMAIL_SENT_D1    = "EMAIL_SENT_D1"    # Day 1 email sent, waiting for open
RESENT_D2        = "RESENT_D2"        # no open on Day 1 → resent Day 2
OPENED           = "OPENED"           # opened at least one email
MOFU_SENT        = "MOFU_SENT"        # follow-up sent after open
CLICKED          = "CLICKED"          # clicked a link
BOFU_SENT        = "BOFU_SENT"        # stronger follow-up sent after click
REPLIED_POSITIVE = "REPLIED_POSITIVE" # classified reply: interested
REPLIED_NEGATIVE = "REPLIED_NEGATIVE" # classified reply: not interested / stop
ENGAGED          = "ENGAGED"          # AI conversation is active
BOUNCED          = "BOUNCED"          # hard bounce — stop all sends
UNSUBSCRIBED     = "UNSUBSCRIBED"     # clicked unsubscribe — stop all sends
DO_NOT_CONTACT   = "DO_NOT_CONTACT"   # negative reply farewell sent — permanent stop
SUNSET           = "SUNSET"           # Day 7 with no engagement — graceful goodbye
COMPLETED        = "COMPLETED"        # campaign finished normally

# States where NO further emails should ever be sent
TERMINAL_STATES = {
    BOUNCED, UNSUBSCRIBED, DO_NOT_CONTACT, SUNSET, COMPLETED
}

# States where the subscriber is still in the sending funnel
ACTIVE_STATES = {
    ACTIVE, EMAIL_SENT_D1, RESENT_D2, OPENED, MOFU_SENT,
    CLICKED, BOFU_SENT, REPLIED_POSITIVE, REPLIED_NEGATIVE, ENGAGED
}
