import os
import time
import pymysql

from flask import Flask, request, jsonify

app = Flask(__name__)

# MySQL 데이터베이스 연결 정보
host = os.getenv('host')
user = os.getenv('user')
password = os.getenv('password')
database = os.getenv('database')

# MySQL 데이터베이스 연결
conn = pymysql.connect(host=host, user=user, password=password, database=database, charset='utf8')

# 커서 생성
cursor = conn.cursor()

@app.route("/")
def home():
    return "Home Page"  # 유효한 응답 반환

@app.route("/", methods=['POST'])
def map_user_info():
    data = request.get_json()
    print("받은 데이터:", data)  # 수신한 데이터 출력
    
    if data is None:
        return "JSON 데이터가 없습니다.", 400  # 잘못된 요청 처리
    
    now = time.localtime()
    print("Android 데이터 전송 받은 시간-%02d:%02d:%02d" % (now.tm_hour, now.tm_min, now.tm_sec))
    
    user_id = 3527954742
    
    # user_place에서 사용자 정보를 가져오는 쿼리
    sql = "SELECT colorcode, place, count FROM user_place WHERE user_id = %s"
    cursor.execute(sql, (user_id,))
    user_place_data = cursor.fetchall()
    
    if user_place_data:
        # count, place, colorcode를 문자열로 연결
        #result_data = ",".join([f"{row[0]}, {row[1]}, {row[2]}" for row in user_place_data])
        result_data = ",".join([f"{str(row[0]).strip()}, {str(row[1]).strip()}, {str(row[2]).strip()}" for row in user_place_data])
        return result_data  # 문자열로 반환
    else:
        return "사용자 장소 정보가 없습니다."

# 고정 서버
@app.route("/server_info")
def server_info():
    data = {'host': MY_IP_ADDRESS, 'port': '5000'}
    return jsonify(data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)
