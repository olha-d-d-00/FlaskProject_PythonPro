import os
import smtplib
import database
from flask import render_template

def queue_filter(email_queue):
    while True:
        data = database.db_session.execute(stmt).fetchall()
        for itm in data:
            email_queue.put(itm)
            # todo: delete data in the db that was put in queue

def send_email_confirmation(email_queue):
    while True:
        one_email = email_queue.get()
        send_email(os.environ.get('EMAIL_USER'), os.environ.get('EMAIL_PASSWORD'), one_email, [])

def send_email(user, pwd, recipient, new_films):

    FROM = os.environ.get("EMAIL_USER")
    TO = recipient if isinstance(recipient, list) else [recipient]
    SUBJECT = "Meet new films"
    if isinstance(new_films, str):
        TEXT = new_films
    else:
        TEXT = render_template("email_template.html", new_films)

    #Prepare email message
    message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(user, pwd)
        server.sendmail(FROM, TO, message)
        server.close()
        print("succesfully sent the email")
    except Exception as e:
        print(f"failed to send mail: {e}")