from flask import Flask, request, jsonify
import time
import json
import pymysql

app = Flask(__name__)

# MySQL 데이터베이스 연결 정보
host = "host"
user = "root"
password = "password"
database = "tourrand"

# MySQL 데이터베이스 연결
conn = pymysql.connect(host=host, user=user, password=password, database=database, charset='utf8')

# 커서 생성
cursor = conn.cursor()

@app.route("/", methods=['POST'])
def delete_users():
    data = request.get_json()
    
    if "ids" in data:
        ids_to_delete = data["ids"]
        
        try:
            # 트랜잭션 시작
            conn.begin()
            
            # 배치 크기 설정
            batch_size = 100
            
            # 배치 단위로 데이터 삭제
            for i in range(0, len(ids_to_delete), batch_size):
                batch_ids = ids_to_delete[i:i+batch_size]
                
                delete_query = "DELETE FROM users WHERE id IN ({})".format(", ".join(["%s"] * len(batch_ids)))
                cursor.execute(delete_query, batch_ids)
                
            # 마지막 일괄 삭제 후 개별 삭제
            if ids_to_delete:
                cursor.execute("DELETE FROM users WHERE id = %s", ids_to_delete[-1])
            
            # 트랜잭션 커밋
            conn.commit()
            
            return "사용자 삭제 완료"
        
        except pymysql.err.OperationalError as e:
            # 락 타임아웃 오류 발생 시 롤백 후 재시도
            conn.rollback()
            print(f"Lock timeout error: {e}")
            
            time.sleep(1)  # 1초 대기 후 재시도
            
            return "사용자 삭제 재시도 중..."
        
        except Exception as e:
            # 기타 오류 발생 시 롤백
            conn.rollback()
            print(f"Error: {e}")
            return "사용자 삭제 실패"
    
    return "요청 데이터 없음"

@app.route("/server_info")
def server_info():
    data = {'host': MY_IP_ADDRESS, 'port':'5000'}
    return jsonify(data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True, port=5000)
