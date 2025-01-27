# 서버 테스트
import os
import time
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    print("test")
    return "Home Page"  # 유효한 응답 반환

@app.route("/", methods=['POST'])
def handle_post():
    message = request.data.decode('utf-8')
    print(message)

    now = time.localtime()
    print("Android 데이터 전송 받은 시간-%02d:%02d:%02dv" % (now.tm_hour, now.tm_min, now.tm_sec))
    
    if json.loads(message).get("content") == "reset":
        return "프로젝트 성공하고 싶어요."  # 유효한 응답 반환
    return "성공 "

@app.route('/message')
def display_message():
    return jsonify(message="Hello, World!")

# test 서버
@app.route("/server_info")
def server_info():
    data = {'host': MY_IP_ADDRESS, 'port':'5000'}
    return jsonify(data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)
