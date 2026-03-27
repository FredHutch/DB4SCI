#!/usr/bin/env python3
import logging
import smtplib

from envelopes import Envelope

from . import mydb_config

smtplib.SMTP.debuglevel = 1

def send_mail(subject, message, TO):
    """send email """
    FROM = mydb_config.MAIL_FROM
    envelope = Envelope(
        from_addr=(FROM, 'DB4SCI'),
        to_addr=(TO),
        subject=subject,
        text_body=message
    )
    SERVER = mydb_config.MAIL_SERVER
    envelope.send(SERVER)
    return None

if __name__ == "__main__":
    import argparse

    subject = "scicomp_srv test"
    message = 'Neither snow nor rain nor heat nor gloom of night stays '
    message += 'this mail agent from the swift completion of its appointed rounds'

    parser = argparse.ArgumentParser(description='send_mail.py unit test')
    parser.add_argument("--mail-to", type=str, required=True)
    args = parser.parse_args()

    addresses = []
    addresses.append(args.mail_to)
    status = send_mail(subject, message, addresses)
    if status:
        print(f'mail not sent to {addresses} reason: {status} ')
