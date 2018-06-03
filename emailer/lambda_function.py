"""
This is a proof of concept to demonstrate how Alexa might be used to support the bids team.
"""

from __future__ import print_function
from bs4 import BeautifulSoup
import requests
from xhtml2pdf import pisa
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
from operator import itemgetter
import boto3
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import json

response = requests.get('https://aws.amazon.com/products/').text


def getServiceList():
    soup = BeautifulSoup(response, 'html.parser')
    serviceList = []
    for service in soup.find_all(class_='lb-content-item'):
        serviceUrl = service.a['href']
        serviceName = service.a.contents[0].strip()
        serviceList.append({'serviceName': serviceName,
                            'serviceUrl': 'https://aws.amazon.com'
                            + serviceUrl})
    return serviceList


def getServiceDescription(serviceUrl):
    response = requests.get(serviceUrl).text
    soup = BeautifulSoup(response, 'html.parser')
    return soup.find('div', {'id': 'aws-page-content'})


def createPdf(serviceUrl):
    outputFilename = '/tmp/service_description.pdf'
    with open(outputFilename, 'w+b') as resultFile:
        pisa.CreatePDF(getServiceDescription(serviceUrl).encode('utf-8'),
                       resultFile)


def findService(serviceName):
    confidenceList = []
    serviceList = getServiceList()
    for service in serviceList:
        service.update({'ratio': fuzz.ratio(service, serviceName)})
        confidenceList.append(service)
    sortedConfidenceList = sorted(confidenceList,
                                  key=itemgetter('ratio'), reverse=True)
    return sortedConfidenceList[0]


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


def getAllParagraphs(url):
    soup = BeautifulSoup(url, 'html.parser')
    paragraphs = []
    content = soup.find(role='main')
    for paragraph in content.find_all('p'):
        if paragraph is not None:
            paragraphs.append(paragraph.text.strip())
    return paragraphs


def sendEmail(serviceUrl, serviceName, emailAddress):
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
    alexa_event = json.loads(event['Records'][0]['Sns']['Message'])
    intent = alexa_event['request']['intent']
    service_name = intent['slots']['service']['value']
    emailProfile = get_user_info(alexa_event['session']['user']['accessToken'])['email']
    service = findService(service_name)
    html = requests.get(service['serviceUrl']).text
    createPdf(service['serviceUrl'])
    resultResponse = sendEmail(service['serviceUrl'], service['serviceName'], emailProfile)
