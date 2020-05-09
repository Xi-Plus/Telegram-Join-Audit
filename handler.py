# -*- coding: utf-8 -*-
import json
import os
import traceback

from flask import Flask, request

from main import System

os.environ['TZ'] = 'UTC'

app = Flask(__name__)


@app.route('/', methods=['GET'])
def index():
    return ''


@app.route('/webhook', methods=['POST'])
def webhook():
    system = System()
    try:
        text = request.data.decode('utf8')
        data = json.loads(text)
        system.main(data)
    except Exception:
        system.log(traceback.format_exc())

    return 'OK'


if __name__ == "__main__":
    app.run()
