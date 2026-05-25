import smtplib
import uuid

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment
from jinja2 import FileSystemLoader

from config import *

env = Environment(
    loader=FileSystemLoader("templates")
)


def send_email(
    subscriber,
    subject,
    html_template,
    text_template
):

    tracking_id = str(uuid.uuid4())

    open_url = (
        f"{BASE_URL}/track/open/{tracking_id}"
    )

    click_url = (
        f"{BASE_URL}/track/click/{tracking_id}"
    )

    unsubscribe_url = (
        f"{BASE_URL}/unsubscribe/{tracking_id}"
    )

    html = env.get_template(
        html_template
    ).render(
        subscriber=subscriber,
        open_url=open_url,
        click_url=click_url,
        unsubscribe_url=unsubscribe_url
    )

    text = env.get_template(
        text_template
    ).render(
        subscriber=subscriber,
        click_url=click_url,
        unsubscribe_url=unsubscribe_url
    )

    msg = MIMEMultipart("alternative")

    msg["Subject"] = subject

    msg["From"] = (
        f"{FROM_NAME} <{FROM_EMAIL}>"
    )

    msg["To"] = subscriber.email

    msg["Reply-To"] = REPLY_TO

    msg["Message-ID"] = (
        f"<{tracking_id}@local>"
    )

    msg["List-Unsubscribe"] = (
        f"<{unsubscribe_url}>"
    )

    msg.attach(
        MIMEText(text, "plain")
    )

    msg.attach(
        MIMEText(html, "html")
    )

    try:

        server = smtplib.SMTP(
            SMTP_HOST,
            SMTP_PORT
        )

        server.starttls()

        server.login(
            SMTP_USERNAME,
            SMTP_PASSWORD
        )

        server.sendmail(
            FROM_EMAIL,
            subscriber.email,
            msg.as_string()
        )

        server.quit()

        return tracking_id, "SENT"

    except Exception as e:

        print("SMTP ERROR:", e)

        return None, "FAILED"