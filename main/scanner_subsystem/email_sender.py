# ECE 5725
# Michael Xiao (mfx2) and Thomas Scavella (tbs47)
# 3D scanner software - Email functionality

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders


class EmailSender:
    """Handles email sending functionality"""
    def __init__(self, email_user, email_password):
        self.email_user = email_user
        self.email_password = email_password

    def send_file(self, recipient, filename, subject='3D File :) !'):
        """Send file via email"""
        msg = MIMEMultipart()
        msg['From'] = self.email_user
        msg['To'] = recipient
        msg['Subject'] = subject

        body = 'Hi there, here is your 3D mesh file!'
        msg.attach(MIMEText(body, 'plain'))

        with open(filename, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {filename}")
            msg.attach(part)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(self.email_user, self.email_password)
        server.sendmail(self.email_user, recipient, msg.as_string())
        server.quit()