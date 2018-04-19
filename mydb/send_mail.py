import smtplib
import local_config


def send_mail(subject, message, to=local_config.var.MAIL_TO):
    """send email """
    if 'yourOrganization' in local_config.var.MAIL_SERVER:
        # config is not setup or running in demo mode
        # return quietly and do not send mail
        return
    SERVER = local_config.var.MAIL_SERVER
    FROM = local_config.var.MAIL_FROM
    TO = to

    message = """\
From: %s
To: %s
Subject: %s

%s
""" % (FROM, ", ".join(TO), subject, message)

    server = smtplib.SMTP(SERVER)
    server.sendmail(FROM, TO, message)
    server.quit()

if __name__ == "__main__":
    subject = "scicomp_srv test"
    message = 'Neither snow nor rain nor heat nor gloom of night stays '
    message += 'this mail delivery agent from the swift completion '
    message += 'of its appointed rounds'

    send_mail(subject, message)
    remote = ["user@yourDomain.org"]
    send_mail(subject, message, remote)
