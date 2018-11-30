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
import hashlib

from os import environ

SNS_EMAIL_TOPIC = environ.get('SNS_EMAIL_TOPIC')

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


def getAllParagraphs(url):
    soup = BeautifulSoup(url, 'html.parser')
    paragraphs = []
    content = soup.find(role='main')
    for paragraph in content.find_all('p'):
        if paragraph is not None:
            paragraphs.append(paragraph.text.strip())
    return paragraphs


def getUrlDigest(url):
    m = hashlib.md5()
    m.update(url.content)
    digest = m.hexdigest()
    return digest


def push_sns(event, snsTopic):
    if os.getenv('AWS_SAM_LOCAL'):
        print('SAM_LOCAL DETECTED')
        sns = boto3.client('sns',
                           endpoint_url='http://localstack:4575',
                           region_name='us-east-1')
    else:
        sns = boto3.client('sns')
    response = sns.publish(
        TopicArn=snsTopic,
        Message=json.dumps(event)
    )
    return response


def build_email(serviceUrl):
    """
    Build the email before sending.
    """
    msg = MIMEMultipart()
    msg.preamble = 'Multipart message.\n'

    # Get the first 3 two paragraphs
    part = MIMEText('Service Description: %r ' %
                    getAllParagraphs(requests.get(serviceUrl).text)[0:2])
    msg.attach(part)

    return msg


# --------------- Main handler ------------------


def lambda_handler(event, context):
    print(event)
    alexa_event = json.loads(event['Records'][0]['Sns']['Message'])
    print(alexa_event)
    intent = alexa_event['request']['intent']
    print(intent)
    service_name = intent['slots']['service']['value']
    service = findService(service_name)
    html = requests.get(service['serviceUrl']).text
    createPdf(service['serviceUrl'])
    message = {}
    message['serviceName'] = service['serviceName']
    message['serviceUrl'] = service['serviceUrl']
    message['body'] = build_email(service['serviceUrl'])
    resultResponse = push_sns(message, SNS_EMAIL_TOPIC)
