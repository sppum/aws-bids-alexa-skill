"""
This is a proof of concept to demonstrate how Alexa might be used to support the bids team.
"""

from __future__ import print_function
import boto3
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import json
import hashlib


def verifyEmail(email):
    client = boto3.client('ses')
    response = client.list_verified_email_addresses()
    if email in response['VerifiedEmailAddresses']:
        return None
    else:
        response = client.verify_email_address(
            EmailAddress=email,
        )
        return True


def sendEmail(emailAddress, kwargs):
    client = boto3.client('ses')
    if verifyEmail(emailAddress) is None:
        msg = MIMEMultipart()
        msg['Subject'] = 'Here is the service description for ' + serviceName
        msg['From'] = emailAddress
        msg['To'] = emailAddress

        msg.preamble = 'Multipart message.\n'

        part = MIMEText('Service description: %r ' %
                        getAllParagraphs(requests.get(serviceUrl).text)[0:2])
        msg.attach(part)

        part = MIMEApplication(open('/tmp/service_description.pdf',
                                    'rb').read())
        part.add_header('Content-Disposition', 'attachment',
                        filename='service_description.pdf')
        msg.attach(part)

        result = client.send_raw_email(RawMessage={
            'Data': msg.as_string()
            },
            Source=msg['From'])
        print(result)
        return "I'm emailing you a service description for " + serviceName
    else:
        return 'Please go to your mail and verify your email address so we can email you the service description'


def get_user_info(access_token):
    amazonProfileURL = 'https://api.amazon.com/user/profile?access_token='
    r = requests.get(url=amazonProfileURL+access_token)
    if r.status_code == 200:
        return r.json()
    else:
        return False

# --------------- Main handler ------------------


def lambda_handler(event, context):
    print(event)
    alexa_event = json.loads(event['Records'][0]['Sns']['Message'])
    print(alexa_event)
    intent = alexa_event['request']['intent']
    print(intent)
    emailProfile = get_user_info(alexa_event['session']['user']['accessToken'])['email']
    print("Email destination: %s" % emailProfile)
#    resultResponse = sendEmail(emailProfile, kwargs)
