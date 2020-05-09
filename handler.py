# -*- coding: utf-8 -*-
import json
import os

from flask import Flask, request

from main import main, log

os.environ['TZ'] = 'UTC'

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return ''


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        text = request.data.decode('utf8')
        data = json.loads(text)
        main(data)
    except Exception as e:
        log(e)
    return 'OK'


if __name__ == "__main__":
    app.run()
