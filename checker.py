import requests
from bs4 import BeautifulSoup as bs
import base64
import json
import time

tokenAntiCaptcha = '...'

def getCaptchaOnBase64():
    image = requests.get("http://gas.kubannet.ru/formvalidator/img.php")

    out = open("captcha.png", "wb")
    out.write(image.content)
    out.close()

    with open("captcha.png", "rb") as image_file:
        encodedString = str(base64.b64encode(image_file.read()))[2:-1]
    return [encodedString, image.cookies]

def solveCaptcha():
    gt = getCaptchaOnBase64()

    captchaString = gt[0]

    headers = {
        'Content-type': 'application/json',
        'Accept': 'text/plain',
        'Content-Encoding': 'utf-8'
    }

    qdata = {
        "clientKey": tokenAntiCaptcha,
        "task": {
            "type": 'ImageToTextTask',
            "body": captchaString,
            "phrase": False,
            "case": True,
            "numeric": False,
            "math": 0,
            "minLenght": 3,
            "maxLenght": 3,
        }
    }

    urlNewTask = 'https://api.anti-captcha.com/createTask'

    while (True):

        resp = requests.post(urlNewTask, data=json.dumps(qdata), headers=headers)
        answer = resp.json()

        if 'taskId' in answer:
            break

    iters = 0

    while (True):

        time.sleep(15)

        urlResultCaptcha = 'https://api.anti-captcha.com/getTaskResult'

        forResultData = {
            "clientKey": tokenAntiCaptcha,
            "taskId": answer['taskId']
        }

        resp = requests.post(urlResultCaptcha, data=json.dumps(forResultData), headers=headers)
        answer = resp.json()

        if 'solution' in answer:
            break

        iters = iters + 1

        if iters == 4:
            break

    if 'solution' in answer:
        return [str(answer['solution']['text']), gt[1]]
    return ['123', gt[1]]

def getCurrentState(examNum, passSerial, passNum):

    gt = solveCaptcha()

    captchaAnswer = gt[0]

    data = {
        's_exam': examNum,
        's_doc_ser': passSerial,
        's_doc_no': passNum,
        's_code': captchaAnswer
    }

    url = 'http://gas.kubannet.ru/?m=114'

    page = requests.post(url, data=data, cookies=gt[1])
    page.encoding = 'cp1251'
    soup = bs(page.text, 'html.parser')

    allB = soup.findAll('b')

    answer = str(allB[-1])[3:-4]

    return answer
