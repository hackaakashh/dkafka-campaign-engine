import smtplib
import uuid

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
    FROM_NAME, FROM_EMAIL, REPLY_TO, BASE_URL
)

env = Environment(loader=FileSystemLoader("templates"))


# ─────────────────────────────────────────────────────────────────
# Kishalay's original function — sends using template files
# ─────────────────────────────────────────────────────────────────
def send_email(subscriber, subject, html_template, text_template):
    tracking_id   = str(uuid.uuid4())
    open_url      = f"{BASE_URL}/track/open/{tracking_id}"
    click_url     = f"{BASE_URL}/track/click/{tracking_id}"
    unsubscribe_url = f"{BASE_URL}/unsubscribe/{tracking_id}"

    html = env.get_template(html_template).render(
        subscriber=subscriber,
        open_url=open_url,
        click_url=click_url,
        unsubscribe_url=unsubscribe_url,
    )
    text = env.get_template(text_template).render(
        subscriber=subscriber,
        click_url=click_url,
        unsubscribe_url=unsubscribe_url,
    )

    return _smtp_send(subscriber.email, subject, html, text, tracking_id)


# ─────────────────────────────────────────────────────────────────
# Akash's addition — sends AI-generated content directly
# ─────────────────────────────────────────────────────────────────
def send_email_direct(subscriber_email, subscriber_name, subject,
                      html_body, text_body, db=None):
    """
    Send email with direct HTML/text content (used by AI agent).
    - Replaces [UNSUBSCRIBE_LINK] placeholder with real URL
    - Injects 1x1 open-tracking pixel into HTML
    - Pre-saves a SENT Event so open/click callbacks can find subscriber
    - Returns (tracking_id, status_string)
    """
    tracking_id     = str(uuid.uuid4())
    open_url        = f"{BASE_URL}/track/open/{tracking_id}"
    click_url       = f"{BASE_URL}/track/click/{tracking_id}"
    unsubscribe_url = f"{BASE_URL}/unsubscribe/{tracking_id}"

    # Replace placeholders the AI inserts
    html_body = html_body.replace("[UNSUBSCRIBE_LINK]", unsubscribe_url)
    html_body = html_body.replace("[CLICK_URL]",        click_url)
    text_body = text_body.replace("[UNSUBSCRIBE_LINK]", unsubscribe_url)
    text_body = text_body.replace("[CLICK_URL]",        click_url)

    # Inject open-tracking pixel at bottom of HTML
    pixel = (
        f'\n<img src="{open_url}" width="1" height="1" '
        f'alt="" style="display:none;"/>'
    )
    html_body = html_body + pixel

    # Pre-save event record so tracking callbacks can resolve subscriber_email
    if db is not None:
        try:
            from models import Event
            pre_event = Event(
                id=str(uuid.uuid4()),
                subscriber_email=subscriber_email,
                tracking_id=tracking_id,
                event_type="SENT",
                metadata="{}",
            )
            db.add(pre_event)
            db.commit()
        except Exception as e:
            print(f"[MAILER] Warning: could not pre-save event: {e}")

    return _smtp_send(subscriber_email, subject, html_body, text_body, tracking_id)


# ─────────────────────────────────────────────────────────────────
# Shared SMTP core
# ─────────────────────────────────────────────────────────────────
def _smtp_send(to_email, subject, html_body, text_body, tracking_id):
    msg = MIMEMultipart("alternative")
    msg["Subject"]         = subject
    msg["From"]            = f"{FROM_NAME} <{FROM_EMAIL}>"
    msg["To"]              = to_email
    msg["Reply-To"]        = REPLY_TO
    msg["Message-ID"]      = f"<{tracking_id}@dkafka.local>"
    msg["List-Unsubscribe"] = f"<{BASE_URL}/unsubscribe/{tracking_id}>"

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(FROM_EMAIL, to_email, msg.as_string())
        server.quit()
        print(f"[MAILER] ✓ SENT → {to_email} | '{subject[:50]}'")
        return tracking_id, "SENT"
    except Exception as e:
        print(f"[MAILER] ✗ SMTP ERROR → {to_email}: {e}")
        return tracking_id, "FAILED"
