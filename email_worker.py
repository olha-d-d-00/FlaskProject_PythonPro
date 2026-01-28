import os
import database, models
import email_sender
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import select

app = Celery("tasks", broker=os.environ["CELERY_BROKER_URL"])


@app.on_after_configure.connect
def setup_periodic_tasks(sender: Celery, **kwargs):
    sender.add_periodic_task(
        crontab(hour=7, minute=30, day_of_week=1),
        build_daily_messages.s()
    )
@app.task
def send_email(subject, body, recipient):
    print(f"Sending email to {recipient}")
    email_sender.send_email(
        os.environ["EMAIL_USER"],
        os.environ["EMAIL_PASSWORD"],
        recipient,
        body
    )

def build_daily_email_only(films):
    if not films:
        return "No new films today"

    lines = ["Newest films:"]
    for film in films:
        lines.append(f"Film name: {film.name}")
    return "\n".join(lines)

@app.task
def build_daily_messages():
    database.init_db()
    # newest_films = execute(select(models.Film).order_by(models.Film.created_at.desc()).limit(10)).all()
    stmt = select(models.Film).order_by(models.Film.created_at.desc()).limit(10)
    newest_films = database.db_session.execute(stmt).scalars().all()
    email_body = build_daily_email_only(newest_films)
    email_recipients = database.db_session.query(models.User).filter(models.User.email != None).all()
    for client in email_recipients:
        send_email.delay("Newest film", email_body, client.email)