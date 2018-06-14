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
import re
import os

response = requests.get('https://aws.amazon.com/products/').text
complianceBucket = os.environ.get('COMPLIANCE_BUCKETNAME')

def getFiles(compliance_name):
    s3 = boto3.resource('s3')
    if re.match(".*27001.*" compliance_name):
        s3.Bucket(complianceBucket).download_file('iso_27001_global_certification.pdf', '/tmp/iso_27001_global_certification.pdf')
        return '/tmp/iso_27001_global_certification.pdf'
    elif re.match(".*27018.*" compliance_name):
        s3.Bucket(complianceBucket).download_file('iso_27018_certification.pdf', '/tmp/iso_27018_certification.pdf')
        return '/tmp/iso_27018_certification.pdf'
    elif re.match(".*soc.*3" compliance_name, re.IGNORECASE):
        s3.Bucket(complianceBucket).download_file('SOC_3.pdf', '/tmp/SOC_3.pdf')
        return '/tmp/SOC_3.pdf'

#def getServiceList():
#    soup = BeautifulSoup(response, 'html.parser')
#    serviceList = []
#    for service in soup.find_all(class_='lb-content-item'):
#        serviceUrl = service.a['href']
#        serviceName = service.a.contents[0].strip()
#        serviceList.append({'serviceName': serviceName,
#                            'serviceUrl': 'https://aws.amazon.com'
#                            + serviceUrl})
#    return serviceList
#
#
#def getServiceDescription(serviceUrl):
#    response = requests.get(serviceUrl).text
#    soup = BeautifulSoup(response, 'html.parser')
#    return soup.find('div', {'id': 'aws-page-content'})
#
#
#def createPdf(serviceUrl):
#    outputFilename = '/tmp/service_description.pdf'
#    with open(outputFilename, 'w+b') as resultFile:
#        pisa.CreatePDF(getServiceDescription(serviceUrl).encode('utf-8'),
#                       resultFile)
#
#
#def findService(serviceName):
#    confidenceList = []
#    serviceList = getServiceList()
#    for service in serviceList:
#        service.update({'ratio': fuzz.ratio(service, serviceName)})
#        confidenceList.append(service)
#    sortedConfidenceList = sorted(confidenceList,
#                                  key=itemgetter('ratio'), reverse=True)
#    return sortedConfidenceList[0]
#
#
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
#
#
#def getAllParagraphs(url):
#    soup = BeautifulSoup(url, 'html.parser')
#    paragraphs = []
#    content = soup.find(role='main')
#    for paragraph in content.find_all('p'):
#        if paragraph is not None:
#            paragraphs.append(paragraph.text.strip())
#    return paragraphs
#
#
#def getUrlDigest(url):
#    m = hashlib.md5()
#    m.update(url.content)
#    digest = m.hexdigest()
#    return digest
#
#
def sendEmail(compliance_name, emailAddress):
    client = boto3.client('ses')
    if verifyEmail(emailAddress) is None:
        msg = MIMEMultipart()
        msg['Subject'] = 'Here is the compliance report for ' + compliance_name
        msg['From'] = emailAddress
        msg['To'] = emailAddress

        msg.preamble = 'Multipart message.\n'

        part = MIMEText('Compliance Report for: ' + compliance_name)
        msg.attach(part)

        complianceReportFile = getFiles(compliance_name)
        part = MIMEApplication(open(complianceReportFile,
                                    'rb').read())
        part.add_header('Content-Disposition', 'attachment',
                        filename='compliance_report.pdf')
        msg.attach(part)

        result = client.send_raw_email(RawMessage={
            'Data': msg.as_string()
            },
            Source=msg['From'])
        print(result)
        return "I'm emailing you a compliance for " + compliance_name
    else:
        return 'Please go to your mail and verify your email address so we can email you the complaince report'
#
#
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
    #print(alexa_event)
    intent = alexa_event['request']['intent']
    #print(intent)
    compliance_name = re.sub(',', '', intent['slots']['compliance']['value'])
    emailProfile = get_user_info(alexa_event['session']['user']['accessToken'])['email']
    sendEmail(compliance_name, emailProfile)
    #service = findService(service_name)
    #html = requests.get(service['serviceUrl']).text
    #createPdf(service['serviceUrl'])
    #resultResponse = sendEmail(service['serviceUrl'], service['serviceName'], emailProfile)
