import os
from flask import Flask, request, jsonify
import json
from collections import OrderedDict
import random
import pymysql
import bcrypt # 일반 회원가입 password 암호화 
from cryptography.fernet import Fernet # 카카오 로그인 암호화
from flask import Response # 아이디 중복확인

import logging
from threading import Thread
from asyncio import as_completed
from concurrent.futures import ThreadPoolExecutor, as_completed

# 캠핑, 생태
import xml.etree.ElementTree as ET
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import requests
from datetime import datetime, timedelta
from openai import OpenAI

# 공공데이터포털에서 발급받은 인증키
service_key = os.getenv('service_key')
weather_service_key=os.getenv('weather_service_key')
camping_service_key=os.getenv('camping_service_key')
eco_service_key=os.getenv('eco_service_key')
youtube_api_key=os.getenv('youtube_api_key')
map_api_key=os.getenv('map_api_key')
MY_IP_ADDRESS=os.getenv('MY_IP_ADDRESS')
api_key = os.getenv('OPENAI_API_KEY') 
client = OpenAI(api_key = service_key)

app = Flask(__name__)

# 카카오 로그인에서 사용
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# # MySQL 데이터베이스 연결 정보
host = os.getenv('host')
user = os.getenv('user')
password = os.getenv('password')
database = os.getenv('database')

# MySQL 연결을 함수 내에서 생성하고 닫는 방식
def get_db_connection():
    return pymysql.connect(host=host, user=user, password=password, database=database, charset='utf8')

# 일반 회원가입
@app.route("/join", methods=['POST'])
def join():
    conn = get_db_connection()
    cursor = conn.cursor()
    try: 
        message = request.data.decode('utf-8')
        data = json.loads(message)
        print(data)
        
        id = data.get('id')
        password = data.get('password').encode('utf-8')  # 비밀번호 인코딩
        nickname = data.get('nickname')

        # ID와 이메일로 사용자 존재 여부 확인
        sql_check = "SELECT id FROM users WHERE id = %s"
        cursor.execute(sql_check, (id,))
        result = cursor.fetchone()
    
        if result is None:
            hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())  # gensalt()로 수정
            sql = "INSERT INTO users (id, nickname, password, account_type) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (id, nickname, hashed_password, 'normal'))
            conn.commit()
            print("회원가입 완료")
            return "회원가입 완료"
        else:
            print("회원가입 실패")
            return "회원가입 실패"
    except pymysql.MySQLError as e:
        print(f"Database error: {e}")
        return "데이터베이스 오류 발생", 500
    except Exception as e:
        print(f"Error: {e}")
        return "서버 오류 발생", 500
    finally:
        cursor.close()
        conn.close()
    
# 일반 로그인 
@app.route("/login", methods=['POST'])
def login():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        data = json.loads(message)
        print(data)
        
        id = data.get('id')
        password = data.get('password').encode('utf-8')
        
        # ID와 이메일로 사용자 존재 여부 확인
        sql_check = "SELECT password FROM users WHERE id = %s"
        cursor.execute(sql_check, (id,))
        result = cursor.fetchone()

        if result:
            # 비밀번호 확인
            stored_password = result[0].encode('utf-8')
            if bcrypt.checkpw(password, stored_password):  # 해시된 비밀번호와 비교
                print("로그인 성공")
                return {"id": id}
            else:
                print("비밀번호가 틀렸습니다.")
                return {"id": "로그인 실패"}, 200
        else:
            print("사용자가 존재하지 않습니다.")
            return {"id": "사용자가 존재하지 않음"}, 200
    finally:
        cursor.close()
        conn.close()

# 아이디 중복 확인 (일반 사용자)
@app.route("/check_id", methods=['POST'])
def check_for_duplicate():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        data = json.loads(message)
        print(data)
        
        id = data.get('id')

        # ID와 이메일로 사용자 존재 여부 확인
        sql_check = "SELECT id FROM users WHERE id = %s"
        cursor.execute(sql_check, (id,))
        result = cursor.fetchone()

        if result is None:
            return "true"
        else:
            return "false"
    finally:
        cursor.close()
        conn.close()

# 카카오 로그인
@app.route("/kakao_login", methods=['POST'])
def kakao_login():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        data = json.loads(message)
        print(data)
        
        id = data.get('id')
        email = data.get('email')
        nickname = data.get('nickname') 
        user_img = data.get('user_img')

        # ID로 사용자 존재 여부 확인
        sql_check = "SELECT * FROM users WHERE id = %s"
        cursor.execute(sql_check, (id,))
        result = cursor.fetchone()

        if result is None:
        # 사용자 존재하지 않으면 회원가입
            sql = "INSERT INTO users (id, email, nickname, user_img, account_type) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql, (id, email, nickname, user_img, 'kakao'))
            conn.commit()
            return jsonify({
                    "nickname": nickname,
                    "invite": "초대 없음" 
                })
        else:
        # 사용자 존재하면 로그인 성공
            sql = "SELECT tour_id, nickname FROM invite WHERE user_id = %s"
            cursor.execute(sql, (id,))
            result = cursor.fetchall()

            if result: 
                tour_id, invite_nickname = result[0] 
                
                sql = "SELECT tour_name FROM tour WHERE tour_id = %s"
                cursor.execute(sql, (tour_id,))
                tour_name = cursor.fetchall()

                return jsonify({ 
                    "tour_id": tour_id,
                    "tour_name": tour_name[0][0],
                    "nickname" : nickname,
                    "invite": "초대 있음",
                    "invite_nickname" : invite_nickname,
                    "isInviteState" : False
                })
            else:
                return jsonify({
                    "nickname": nickname,
                    "invite": "초대 없음" 
                })
    finally:
        cursor.close()
        conn.close()

# 카카오 로그인 (초대 다이얼로그)
@app.route("/invite_delete", methods=['POST'])
def updateInviteStatus():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        data = json.loads(message)
        
        user_id = data.get('user_id')
        tour_id = data.get('tour_id')
        
        sql_delete = "DELETE FROM invite WHERE user_id = %s AND tour_id = %s"
        cursor.execute(sql_delete, (user_id, tour_id))
        conn.commit()
        
        return "삭제 완료"
    finally:
        cursor.close()
        conn.close()

@app.route("/second_route", methods=['POST'])
def second_route():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        data = json.loads(message)
        
        date_str = data.get('day')  # 일정
        date = int(date_str) # 일정 개수
        count = generate_itinerary(date)
        
        theme = "empty"

        destinations = ["강릉", "강화도", "거제", "경주", "고양", "공주", "광주광역시",
        "나주", "남양주", "남원", "대구", "대전", "밀양", "보령", "보성", "봉화", "부산", "부여", "산청", "삼척", "서울", "안동", "안성", "양평", "여수", "연천", "영동", "울산", "인천", "제주도", "제천", "창원", "청주", "춘천", "충주", "태안", "파주", "평창", "포천", "포항"
        ]
        destination = random.choice(destinations)
        

        # 메인테마에 맞는 장소 조회
        sql = "SELECT DISTINCT place_name, full_address, longitude, latitude FROM place WHERE sec_place = %s AND full_address IS NOT NULL ORDER BY RAND() LIMIT %s"
        cursor.execute(sql, (destination, sum(count)))
        combined_places = cursor.fetchall()
        
        print(combined_places)

        # 위도 경도 장소 이름
        places_list = [
            {
                "place_name": row[0],
                "full_address": row[1].replace("NULL", "").strip(),
                "longitude": row[2], 
                "latitude": row[3]  
            } for row in combined_places
        ]

        if not places_list:
            print("places_list가 비어있습니다.")
        
        itinerary_json = second_generate_and_chat(places_list, date, cursor, destination, theme, count)
        
        # 빈 리스트 체크 및 재실행
        if len(itinerary_json) == 0:
            try:
                # 재조회 함수 호출
                return handle_empty_itinerary(cursor, destination, theme, count, date)
            except Exception as e:
                return {"error": f"재조회 중 오류가 발생했습니다: {str(e)}"}
        
        response_json = {
            "itinerary": itinerary_json,
            "destination": destination
        }
            
        print (response_json)
        return jsonify(response_json)
    finally:
        cursor.close()
        conn.close()

# 장소 부족으로 다시 돌리는 경우에 필요한 재귀호출 함수 
def handle_empty_itinerary(cursor, destination, theme, count, date):
    places_list = fetch_places(cursor, destination, theme, count)
    itinerary_json = second_generate_and_chat(places_list, date, cursor, destination, theme, count)  # 재귀 호출로 일정 생성

    if itinerary_json:
        response_json = {
            "itinerary": itinerary_json,
            "destination": destination
        }
        print("재귀호출 들어왔음")
        return jsonify(response_json)
    else:
        print("재귀호출 실패 !")
        return handle_empty_itinerary(cursor, destination, theme, count, date)
    
# 경로 생성
@app.route("/route", methods=['POST'])
def route():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        data = json.loads(message)
        
        date_str = data.get('day')  # 일정
        theme = data.get('mainTheme') # 메인테마
        destination = data.get('destination') # 목적지
        
        date = int(date_str) # 일정 개수
        count = generate_itinerary(date)
        
        print(date_str, theme, destination)
        
        half_count = (sum(count) * 2) // 3  # 메인테마에 맞는 개수 
        
        # 메인테마에 맞는 장소 조회
        sql = "SELECT DISTINCT place_name, full_address, longitude, latitude FROM place WHERE sec_place = %s AND (theme1 = %s OR theme2 = %s) AND full_address IS NOT NULL ORDER BY RAND() LIMIT %s"
        cursor.execute(sql, (destination, theme, theme, half_count))
        random_places = cursor.fetchall()
        
        # 테마와 상관없이
        sql_all = "SELECT DISTINCT place_name, full_address, longitude, latitude FROM place WHERE sec_place = %s AND (theme1 != %s AND theme2 != %s) AND full_address IS NOT NULL ORDER BY RAND() LIMIT %s"
        cursor.execute(sql_all, (destination, theme, theme, sum(count) - half_count))
        all_places = cursor.fetchall()
        
        combined_places = list(random_places) + list(all_places) 

        total_needed = sum(count) - len(combined_places)
        if total_needed > 0:
            sql_total = "SELECT DISTINCT place_name, full_address, longitude, latitude FROM place WHERE sec_place = %s AND full_address IS NOT NULL ORDER BY RAND() LIMIT %s"
            cursor.execute(sql_total, (destination, total_needed))
            additional_places = cursor.fetchall()
            combined_places += list(additional_places)

        print (combined_places)

        # 위도 경도 장소 이름
        places_list = [
            {
                "place_name": row[0],
                "full_address": row[1].replace("NULL", "").strip(),
                "longitude": row[2], 
                "latitude": row[3]  
            } for row in combined_places
        ]

        if not places_list:
            print("places_list가 비어있습니다.")
        
        itinerary_json = generate_and_chat(places_list, date, cursor, destination, theme, half_count, count)
        
        # 빈 리스트 체크 및 재실행
        if itinerary_json == "장소부족":
            return "장소부족"
            
        return jsonify(itinerary_json)
    finally:
        cursor.close()
        conn.close()
        
# 일정 개수 생성
def generate_itinerary(date):
    daily_plan = []
    if date == 1:
        daily_plan = [3]
    elif date == 2:
        daily_plan = [3, 3]
    elif date >= 3:
        daily_plan.append(2)
        for _ in range(1, date - 1):
            daily_plan.append(3)
        daily_plan.append(2)
    return daily_plan

# 두번째 GPT 일정 생성
def second_generate_and_chat(places, date, cursor, destination, theme, count, model="gpt-3.5-turbo", max_tokens=2000):
    places_info = "\n".join([f"{place['place_name']} {place['longitude']} {place['latitude']}" for place in places])
    
    daily_plan = generate_itinerary(date)
    day_prompts = " ".join([f"{i+1}일차 ({count}장소):" for i, count in enumerate(daily_plan)])
    
    prompt = f"""
    {places_info}
    이 장소들을 전부 포함해서 최적의 여행 일정을 짜줘.
    {day_prompts}
    각 장소는 '1일차:'와 같은 형식으로 나눠서 작성해줘.
    인사와 (1 장소), (2 장소), 아침, 점심 등 부가설명 생략해.
    각 장소 다음에는 무조건 줄바꿈해줘.
    """

    try:
        response = client.chat.completions.create(    
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        itinerary_text = response.choices[0].message.content.strip() 
        
        daywise_places = {place['place_name']: place for place in places}

        if "없음" in itinerary_text:
            return []
        
        itinerary_json = parse_itinerary(itinerary_text, daywise_places)
        
        return itinerary_json 
    except Exception as e:
        print(f"오류 발생: {e}")
        try:
            places_list = fetch_places(cursor, destination, theme, count)
            return second_generate_and_chat(places_list, date, cursor, destination, theme, count)  # 재귀 호출로 일정 생성
        except Exception as e:
            return {"error": f"재조회 중 오류가 발생했습니다: {str(e)}"}

# GPT 일정 생성
def generate_and_chat(places, date, cursor, destination, theme, half_count, count, model="gpt-3.5-turbo", max_tokens=2000):
    places_info = "\n".join([f"{place['place_name']} {place['longitude']} {place['latitude']}" for place in places])
    
    daily_plan = generate_itinerary(date)
    day_prompts = " ".join([f"{i+1}일차 ({count}장소):" for i, count in enumerate(daily_plan)])
    
    prompt = f"""
    {places_info}
    이 장소들을 전부 포함해서 최적의 여행 일정을 짜줘.
    {day_prompts}
    각 장소는 '1일차:'와 같은 형식으로 나눠서 작성해줘.
    인사와 (1 장소), (2 장소), 아침, 점심 등 부가설명 생략해.
    각 장소 다음에는 무조건 줄바꿈해줘.
    장소 중복하지마. 부족하면 '없음' 이라고 말해.
    """
    
    #print("프롬프트 내용:", prompt)  # 프롬프트 로그 추가

    try:
        response = client.chat.completions.create(    
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=0.7
        )
        itinerary_text = response.choices[0].message.content.strip() 
        print("GPT 응답:", itinerary_text)  # GPT 응답 로그 추가
        
        # 장소 정보를 이름을 키로 하여 딕셔너리로 저장
        daywise_places = {place['place_name']: place for place in places}

        # 일정 텍스트를 줄 단위로 나누고, '1일차:', '2일차:' 등 구분 텍스트를 제외한 실제 장소만 필터링
        itinerary_lines = [line.strip() for line in itinerary_text.splitlines() if line.strip() and not any(day_marker in line for day_marker in ['1일차', '2일차', '3일차', '4일차', '5일차', '6일차', '7일차', '8일차', '9일차', '10일차'])]

        days_with_places = []
        for i, line in enumerate(itinerary_text.splitlines()):
            if f"{i+1}일차" in line:
                # 해당 일차에 '없음'이 포함되어 있는 경우 처리
                if "없음" in line:
                    # 다음 줄들 중 장소가 있는지 확인 (다음 날이 나오면 그만 검사)
                    has_place = False
                    unique_places = set()  # 중복된 장소 확인을 위한 집합
                    for j in range(i + 1, len(itinerary_text.splitlines())):
                        next_line = itinerary_text.splitlines()[j].strip()
                        # 다음 날(day marker)이 나오면 중단
                        if any(day_marker in next_line for day_marker in ['1일차', '2일차', '3일차', '4일차', '5일차', '6일차', '7일차', '8일차', '9일차', '10일차']):
                            break
                        # 장소가 있고 중복되지 않으면 True로 설정
                        if next_line and "없음" not in next_line:
                            if next_line not in unique_places:
                                unique_places.add(next_line)
                                has_place = True
                            else:
                                # 중복된 장소는 무시
                                has_place = False
                                continue
                    
                    # 해당 날에 장소가 없거나 중복된 장소만 있으면 "장소부족" 반환
                    if not has_place:
                        return "장소부족"
                else:
                    days_with_places.append(line)

        # 만약 마지막 날까지 검사한 후 장소가 없는 날 또는 중복된 장소만 있는 날이 있다면 "장소부족" 반환
        if not days_with_places or all("없음" in day or len(set(day)) != len(day) for day in days_with_places[-2:]):  # 마지막 2일(9일차, 10일차)에 장소가 없거나 중복되면
            return "장소부족"

        # 전체 일정에서 등장한 장소 수 계산
        itinerary_place_count = len(itinerary_lines)
        required_place_count = sum(count)  # 필요한 장소 수

        # 필요한 장소 수의 75% 이상인 경우 일정 JSON 생성
        if itinerary_place_count >= (required_place_count * 3) // 4:
            itinerary_json = parse_itinerary(itinerary_text, daywise_places)
            return itinerary_json

        # 부족한 경우 "장소부족" 반환
        return itinerary_json

    except Exception as e:
        print(f"오류 발생: {e}")
        try:
            places_list = fetch_places(cursor, destination, theme, count)
            return generate_and_chat(places_list, date, cursor, destination, theme, half_count, count, model="gpt-3.5-turbo", max_tokens=2000)  # 재귀 호출로 일정 생성
        except Exception as e:
            return {"error": f"재조회 중 오류가 발생했습니다: {str(e)}"}
        
def fetch_places(cursor, destination, theme, count):
    
    half_count = (sum(count) * 2) // 3 
       
    combined_places = []
    
    if theme == "empty":  # 테마가 empty일 경우
        # 테마에 상관없이 장소 조회
        sql = "SELECT DISTINCT place_name, full_address, longitude, latitude FROM place WHERE sec_place = %s AND full_address IS NOT NULL ORDER BY RAND() LIMIT %s"
        cursor.execute(sql, (destination, sum(count)))
        combined_places = cursor.fetchall()
    else:
        # 메인테마에 맞는 장소 조회
        sql = "SELECT DISTINCT place_name, full_address, longitude, latitude FROM place WHERE sec_place = %s AND (theme1 = %s OR theme2 = %s) AND full_address IS NOT NULL ORDER BY RAND() LIMIT %s"
        cursor.execute(sql, (destination, theme, theme, half_count))
        random_places = cursor.fetchall()

        # 테마와 상관없이 장소 조회
        sql_all = "SELECT DISTINCT place_name, full_address, longitude, latitude FROM place WHERE sec_place = %s AND (theme1 != %s AND theme2 != %s) AND full_address IS NOT NULL ORDER BY RAND() LIMIT %s"
        cursor.execute(sql_all, (destination, theme, theme, sum(count) - half_count))
        all_places = cursor.fetchall()

        combined_places = list(random_places) + list(all_places)
    
    # 부족한 장소가 있을 경우 추가 조회
    total_needed = sum(count) - len(combined_places)
    
    if total_needed > 0:
        sql_total = "SELECT DISTINCT place_name, full_address, longitude, latitude FROM place WHERE sec_place = %s AND full_address IS NOT NULL ORDER BY RAND() LIMIT %s"
        cursor.execute(sql_total, (destination, total_needed))
        additional_places = cursor.fetchall()
        combined_places += list(additional_places)

    if not combined_places:
        print("combined_places가 비어 있습니다.")
    else:
        print("combined_places:", combined_places)
        
    places_list = [
        {
            "place_name": row[0],
            "full_address": row[1].replace("NULL", "").strip(),
            "longitude": row[2], 
            "latitude": row[3]  
        } for row in combined_places if len(row) >= 4 
    ]
  
    return places_list

# 일정 반환
def parse_itinerary(itinerary_text, daywise_places):
    itinerary = []
    lines = itinerary_text.splitlines()

    current_day = 1  # 기본값으로 1일차 설정

    for line in lines:
        if not line.strip():
            continue
        line = line.lstrip('- ').strip()
        
        if ":" in line:
            day, location = line.split(":", 1)
            day = day.strip().replace("일차", "")
            
            current_day = int(day)  # 현재 날짜 업데이트
        else:
            location = line.strip()
        
        # 장소 정보를 찾기
        place_info = daywise_places.get(location)
        if place_info:
            latitude = place_info['latitude']
            longitude = place_info['longitude']
            full_address = place_info['full_address']
            
            # 장소 추가
            itinerary.append({
                "day": str(current_day),
                "location": location.strip(),
                "address": full_address,
                "latitude": float(latitude),
                "longitude": float(longitude)
            })
    
    return itinerary

# 일정 확정
@app.route("/confirmed", methods=['POST'])
def confirmed():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        print(f"Received message: {message}")

        if not message:
            return jsonify({"error": "빈 요청 데이터"}), 400

        try:
            itinerary = json.loads(message)
        except json.JSONDecodeError as e:
            return jsonify({"error": "잘못된 JSON 형식", "details": str(e)}), 400

        user_id = itinerary.get('user_id')
        tour_name = itinerary.get('tour_name')
        planDate = itinerary.get('planDate')

        destination = itinerary.get('destination')

        team_name = generate_random_team_name()

        # 새로운 팀 생성
        cursor.execute("INSERT INTO team (name) VALUES (%s)", (team_name,))
        conn.commit()

        # 생성된 팀의 ID 가져오기
        team_id = cursor.lastrowid

        # tour 테이블에 추가하는 부분
        sql_insert = "INSERT INTO tour (user_id, tour_name, planDate, team_id) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql_insert, (user_id, tour_name, planDate, team_id))
        conn.commit()

        # 추가된 tour_id 가져오기
        sql_select = """SELECT tour_id FROM tour WHERE user_id = %s AND tour_name = %s AND planDate = %s AND team_id = %s"""
        cursor.execute(sql_select, (user_id, tour_name, planDate, team_id))
        tour_id_row = cursor.fetchone()

        if tour_id_row is None:
            return jsonify({"error": "투어 ID를 가져오는 데 실패했습니다."}), 400

        tour_id = tour_id_row[0]

        # 팀 멤버로 사용자 추가
        cursor.execute("INSERT INTO team_members (user_id, team_id, tour_id) VALUES (%s, %s, %s)", (user_id, team_id, tour_id))
        conn.commit()

        # roulette 테이블에 추가하는 부분
        sql = "INSERT INTO roulette_results (user_id, tour_id, count) VALUES (%s, %s, %s)"
        cursor.execute(sql, (user_id, tour_id, 0))  # count 값으로 0을 추가
        conn.commit()

        # 여행 일정 확정부분
        order_index = 1
        for schedule in itinerary.get("schedules", []):
            sql = """INSERT INTO schedules (team_id, user_id, day, `order`, location, address, longitude, latitude, planDate, tour_name, tour_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            values = (
                team_id,
                user_id,
                schedule.get("day"),
                order_index,
                schedule.get("location"),
                schedule.get("address"),
                schedule.get("longitude"),
                schedule.get("latitude"),
                planDate,
                tour_name,
                tour_id
            )
            try:
                cursor.execute(sql, values)
            except Exception as e:
                return jsonify({"error": f"일정 추가 중 오류 발생: {str(e)}"}), 500
            order_index += 1

        # user_place 테이블에 장소 추가
        try:
            sql_place = "INSERT INTO user_place (user_id, place, tour_id, count) VALUES (%s, %s, %s,%s)"
            cursor.execute(sql_place, (user_id, destination, tour_id, 1))
        except Exception as e:
            return jsonify({"error": f"장소 추가 중 오류 발생: {str(e)}"}), 500

        conn.commit()  # 모든 삽입 작업이 끝난 후에 commit 호출

        return jsonify({"message": "일정 확정 완료"})
    finally:
        cursor.close()
        conn.close()

# 팀원 추가 요청 (메시지 보내기 전)
@app.route("/invite", methods=['POST'])
def invite():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        itinerary = json.loads(message)

        users = itinerary.get('users')  # 사용자 정보 배열
        tour_id = itinerary.get('tour_id')  # 투어 ID
        nickname = itinerary.get('nickname')  # 닉네임

        for user in users:
            user_id = user.get('user_id')  # 각 사용자의 ID

            print(user_id, tour_id, nickname)

            sql_insert = "INSERT INTO invite (tour_id, user_id, nickname) VALUES (%s, %s, %s)"
            cursor.execute(sql_insert, (tour_id, user_id, nickname))

        conn.commit()  # 모든 초대 정보를 처리한 후 커밋

        return "팀원 추가 요청 완료"
    finally:
        cursor.close()
        conn.close()

# 팀원 추가 (메시지 받고 확인 눌러서 진짜 들어옴)
@app.route("/add", methods=['POST'])
def add_member():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        message = request.data.decode('utf-8')
        itinerary = json.loads(message)

        user_id = itinerary.get('user_id')
        tour_id = itinerary.get('tour_id')

        # roulette 테이블에 추가하는 부분
        sql = "INSERT INTO roulette_results (user_id, tour_id, count) VALUES (%s, %s, %s)"
        cursor.execute(sql, (user_id, tour_id, 0))  # count 값으로 0을 추가

        # 팀 ID 조회 쿼리
        sql_query = "SELECT team_id FROM tour WHERE tour_id = %s"
        cursor.execute(sql_query, (tour_id,))
        result = cursor.fetchone()

        if result:  # team_id가 존재하는지 확인
            team_id = result[0]  # 첫 번째 요소에서 team_id 추출

            # 팀원 추가 쿼리
            sql_insert = "INSERT INTO team_members (user_id, team_id, tour_id) VALUES (%s, %s, %s)"
            cursor.execute(sql_insert, (user_id, team_id, tour_id))
            conn.commit()

            # 기존 schedules 데이터 조회
            sql_select_schedules = "SELECT day, `order`, address, longitude, latitude, planDate, tour_name, location FROM schedules WHERE tour_id = %s"
            cursor.execute(sql_select_schedules, (tour_id,))
            schedules = cursor.fetchall()

            # 사용자 ID로 schedules에 추가
            for schedule in schedules:
                sql_insert_schedule = """
                INSERT INTO schedules (team_id, user_id, day, `order`, address, longitude, latitude, planDate, tour_name, location, tour_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert_schedule, (team_id, user_id, *schedule, tour_id))

            conn.commit()
            
            # user_place에서 place 조회
            sql_place_query = "SELECT place FROM user_place WHERE tour_id = %s"
            cursor.execute(sql_place_query, (tour_id,))
            place_row = cursor.fetchone()

            if place_row:  # place가 존재하는 경우
                place = place_row[0]
                sql_place = "INSERT INTO user_place (user_id, count, place, tour_id) VALUES (%s, %s, %s, %s)"
                cursor.execute(sql_place, (user_id, 1, place, tour_id))
            else:
                print("user_place에서 place를 찾을 수 없습니다.")

            # 초대 삭제
            sql_delete = "DELETE FROM invite WHERE user_id = %s AND tour_id = %s"
            cursor.execute(sql_delete, (user_id, tour_id))  # user_id 변수 사용
            conn.commit()

            return "팀원 추가 완료"
        else:
            return jsonify({"error": "해당 투어에 대한 팀 ID를 찾을 수 없습니다."}), 404
    finally:
        cursor.close()
        conn.close()
   
# 팀원 확인 (멤버 확인)
@app.route("/checkteam", methods=['POST'])
def check_team_members():
    message = request.data.decode('utf-8')
    itinerary = json.loads(message)
    
    tour_id = itinerary.get('tour_id')
    user_id = itinerary.get('user_id')

    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # 팀 ID 조회 쿼리
        sql_query = "SELECT team_id FROM tour WHERE tour_id = %s"
        cursor.execute(sql_query, (tour_id,))
        result = cursor.fetchone()  # 여기서 team_id 추출
        
        if result:  # team_id가 존재하는지 확인
            team_id = result[0]  # 첫 번째 요소에서 team_id 추출
            
            sql_members_query = """
                SELECT DISTINCT u.nickname 
                FROM team_members tm
                JOIN users u ON tm.user_id = u.id
                WHERE tm.team_id = %s AND tm.user_id != %s AND tm.tour_id = %s
            """
            cursor.execute(sql_members_query, (team_id, user_id, tour_id))
            members = cursor.fetchall()

            if members:  # members가 비어있지 않은지 확인
                nicknames = [member[0] for member in members]
                return jsonify({"message": True, "member": nicknames})
            else:
                return jsonify({"message": False})
        else:
            return jsonify({"message": False})


# 팀 이름 랜덤 생성     
def generate_random_team_name():
    adjectives = ["Amazing", "Fantastic", "Incredible", "Epic", "Brilliant"]
    nouns = ["Adventurers", "Explorers", "Wanderers", "Travelers", "Voyagers"]
    return f"{random.choice(adjectives)} {random.choice(nouns)}"

# 투어 리스트 가져오기
@app.route("/tour_list", methods=['POST'])
def tour_list():
    message = request.data.decode('utf-8')
    message = json.loads(message)

    user_id = message.get('user_id')

    if not user_id:
        return jsonify({"error": "User ID is required."}), 400

    if isinstance(user_id, list):
        user_id = list(set(user_id))[0]

    if isinstance(user_id, str):
        user_id = user_id.strip()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        sql = """
        SELECT DISTINCT t.tour_id
        FROM team_members tm
        JOIN tour t ON tm.team_id = t.team_id
        WHERE tm.user_id = %s
        """
        
        cursor.execute(sql, (user_id,))
        tour_ids = cursor.fetchall()

        tour_ids_tuple = tuple(tour_id[0] for tour_id in tour_ids)

        if len(tour_ids_tuple) == 0:
            return jsonify([])  # 투어 ID가 없을 경우 빈 리스트 반환
        else:
            placeholders = ', '.join(['%s'] * len(tour_ids_tuple))  
            query = f"""
            SELECT t.tour_name, t.planDate, u.user_img, t.tour_id
            FROM tour t
            JOIN team_members tm ON t.team_id = tm.team_id
            JOIN users u ON tm.user_id = u.id
            WHERE t.tour_id IN ({placeholders})
            """
            cursor.execute(query, tour_ids_tuple)
            tours = cursor.fetchall()

        result = {}
        for tour in tours:
            tour_name = tour[0]
            plan_date = tour[1]
            user_img = tour[2]
            tour_id = tour[3]

            if tour_id not in result:
                result[tour_id] = {
                    "tour_name": tour_name,
                    "planDate": plan_date,
                    "user_imgs": []  
                }
            
            result[tour_id]["user_imgs"].append(user_img)

        final_result = []
        for tour_id, details in result.items():
            final_result.append({
                "planDate": details["planDate"],
                "user_imgs": details["user_imgs"],
                "tour_name": details["tour_name"],
                "tour_id": tour_id
            })

        return jsonify(final_result)


# 일정 전체 삭제
@app.route("/delete", methods=['POST'])
def delete_all():
    message = request.data.decode('utf-8')
    itinerary = json.loads(message)

    user_id = itinerary.get('user_id')
    tour_id = itinerary.get('tour_id')

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("DELETE FROM invite WHERE tour_id = %s", (tour_id,))
        cursor.execute("DELETE FROM schedules WHERE tour_id = %s", (tour_id,))
        cursor.execute("DELETE FROM tour WHERE tour_id = %s", (tour_id,))
        cursor.execute("DELETE FROM user_place WHERE tour_id = %s", (tour_id,))
        cursor.execute("DELETE FROM team_members WHERE tour_id = %s", (tour_id,))
        conn.commit()

        sql = """
        SELECT DISTINCT t.tour_id
        FROM team_members tm
        JOIN tour t ON tm.team_id = t.team_id
        WHERE tm.user_id = %s
        """
        
        cursor.execute(sql, (user_id,))
        tour_ids = cursor.fetchall()

        tour_ids_tuple = tuple(tour_id[0] for tour_id in tour_ids)

        if not tour_ids_tuple:
            return jsonify([])  # 투어 ID가 없을 경우 빈 리스트 반환

        placeholders = ', '.join(['%s'] * len(tour_ids_tuple))  
        query = f"""
        SELECT t.tour_name, t.planDate, u.user_img, t.tour_id
        FROM tour t
        JOIN team_members tm ON t.team_id = tm.team_id
        JOIN users u ON tm.user_id = u.id
        WHERE t.tour_id IN ({placeholders})
        """
        
        cursor.execute(query, tour_ids_tuple)
        tours = cursor.fetchall()

        result = {}
        for tour in tours:
            tour_name = tour[0]
            plan_date = tour[1]
            user_img = tour[2]
            tour_id = tour[3]

            if tour_id not in result:
                result[tour_id] = {
                    "tour_name": tour_name,
                    "planDate": plan_date,
                    "user_imgs": []  
                }
            
            result[tour_id]["user_imgs"].append(user_img)

        final_result = []
        for tour_id, details in result.items():
            final_result.append({
                "planDate": details["planDate"],
                "user_imgs": details["user_imgs"],
                "tour_name": details["tour_name"],
                "tour_id": tour_id
            })

        return jsonify(final_result)

# 일정 편집
@app.route("/update_itinerary", methods=['POST'])
def update_itinerary():
    message = request.data.decode('utf-8')
    itinerary = json.loads(message)
    
    user_id = itinerary.get('user_id')
    tour_name = itinerary.get('tour_name')
    planDate = itinerary.get('planDate') 
    tour_id = itinerary.get('tour_id')

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # 기존 일정 삭제
            cursor.execute("DELETE FROM invite WHERE tour_id = %s", (tour_id,))
            cursor.execute("DELETE FROM schedules WHERE tour_id = %s", (tour_id,))
            cursor.execute("DELETE FROM tour WHERE tour_id = %s", (tour_id,))

            # 팀 ID 가져오기
            cursor.execute("SELECT team_id FROM team_members WHERE user_id = %s AND tour_id = %s", (user_id, tour_id))
            team = cursor.fetchone()

            if team:
                team_id = team[0]  # team_id가 있을 경우 가져오기
            
            # tour 테이블에 추가하는 부분
            sql_insert = "INSERT INTO tour (tour_id, user_id, tour_name, planDate, team_id) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(sql_insert, (tour_id, user_id, tour_name, planDate, team_id))
            conn.commit()  # 여기서 commit

            # 추가된 tour_id 가져오기
            sql_select = """SELECT tour_id FROM tour WHERE user_id = %s AND tour_name = %s AND planDate = %s"""
            cursor.execute(sql_select, (user_id, tour_name, planDate))
            tour_id_row = cursor.fetchone()

            # tour_id_row가 None인 경우 처리
            if tour_id_row is None:
                return "투어가 존재하지 않습니다.", 404  # 오류 메시지 반환

            tour_id = tour_id_row[0]  # tour_id 가져오기
            
            # 팀원 목록 가져오기
            cursor.execute("SELECT user_id FROM team_members WHERE team_id = %s", (team_id,))
            team_members = cursor.fetchall()
                
            # 새로운 일정 추가
            order_index = 1
            for schedule in itinerary.get("schedules", []):
                for member in team_members:
                    member_id = member[0]
                    sql = """INSERT INTO schedules (team_id, user_id, day, `order`, location, address, longitude, latitude, planDate, tour_name, tour_id)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                    values = (
                        team_id,
                        member_id,
                        schedule.get("day"),
                        order_index,
                        schedule.get("location"),
                        schedule.get("address"),
                        schedule.get("longitude"),
                        schedule.get("latitude"),
                        planDate,
                        tour_name,
                        tour_id
                    )
                    cursor.execute(sql, values)
                order_index += 1
                
            conn.commit()  # 모든 작업이 성공적으로 끝난 후 commit

        return "변경되었습니다."
    
    except Exception as e:
        logging.error(f"오류 발생: {str(e)}")
        return jsonify({"error": f"오류 발생: {str(e)}"}), 500


# 일정 상세하게 보여주기
@app.route("/tour_detail", methods=['POST'])
def tour_detail():
    data = request.get_json()
    user_id = data.get('user_id') 
    tour_id = data.get('tour_id') 

    print(user_id, tour_id)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        sql = "SELECT tour_name FROM tour WHERE tour_id = %s"
        cursor.execute(sql, (tour_id,))
        tour_name = cursor.fetchone()
        
        if tour_name:
            tour_name = tour_name[0] 
    
        sql = """
        SELECT day, location, address, longitude, latitude 
        FROM schedules 
        WHERE tour_id = %s
        AND user_id = %s
        ORDER BY `order` ASC
        """
        cursor.execute(sql, (tour_id, user_id))

        itinerary = cursor.fetchall()
        details = []
        for item in itinerary:
            details.append({
                "day": item[0],
                "location": item[1],  
                "address": item[2],
                "longitude": item[3],
                "latitude": item[4] 
            })

    response = {
        "tour_name" : tour_name,
        "details": details
    }

    print(details)
    return jsonify(response)


# 반려동물 일정 생성
@app.route("/pet", methods=['POST'])
def pet():
    message = request.data.decode('utf-8')
    data = json.loads(message)
    
    date_str = data.get('day')  # 일정
    destination = data.get('destination')  # 목적지
    
    date = int(date_str)  # 일정 개수
    daily_plan = generate_itinerary(date)
    count = sum(daily_plan)  # daily_plan 리스트의 요소들을 합산하여 count로 사용
    
    # count가 정수인지 확인합니다.
    if not isinstance(count, int):
        return jsonify({"error": "Internal server error: Invalid itinerary count."}), 500

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 반려동물 장소 조회 쿼리
        sql_all = "SELECT place_name, full_address, longitude, latitude FROM pet_place WHERE sec_place = %s ORDER BY RAND() LIMIT %s"
        cursor.execute(sql_all, (destination, count))
        pet_places = cursor.fetchall()

    places_list = [
        {
            "place_name": row[0],
            "full_address": row[1].replace("NULL", "").strip(),  
            "longitude": row[2], 
            "latitude": row[3]  
        } for row in pet_places 
    ]
    print("Places List:", places_list)
    
    itinerary_json = generate_and_chat(places_list, date)
    print("Itinerary JSON:", itinerary_json)
    
    return jsonify(itinerary_json)


# 지도 색칠
@app.route("/map", methods=['POST'])
def map():
    message = request.data.decode('utf-8')
    data = json.loads(message)
    
    user_id = data.get('user_id')
    
    if user_id is None:
        return jsonify({"error": "id가 없음"}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 현재 날짜 가져오기
        current_date = datetime.now().date()  # 날짜 형식으로 변환

        # tour 테이블에서 planDate가 문자열로 저장된 것을 가져오기
        query = "SELECT tour_id, planDate FROM tour where user_id = %s"
        cursor.execute(query, (user_id,))
        result = cursor.fetchall()

        # 문자열로 저장된 planDate에서 끝나는 날짜를 추출하고 비교
        for row in result:
            tour_id, plan_date_str = row

            # 예: '2024-09-27~2024-09-28' 형식의 문자열에서 끝나는 날짜 추출
            try:
                start_date, end_date = plan_date_str.split('~')
                end_date = end_date.strip()  # 공백 제거
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            except ValueError:
                continue  # 날짜 형식이 잘못된 경우 건너뜀

            print(f"Current date: {current_date}, End date: {end_date}")

            # 끝나는 날짜가 현재 날짜보다 이르거나 같으면 colorcode 업데이트
            if end_date <= current_date:
                # 0~4 사이의 랜덤 숫자를 생성하여 user_place 테이블의 colorcode 업데이트
                random_number = random.randint(0, 4)
                update_query = "UPDATE user_place SET colorcode = %s WHERE tour_id = %s AND user_id = %s"
                cursor.execute(update_query, (random_number, tour_id, user_id)) 
                if cursor.rowcount == 0:
                    print(f"No rows updated for tour_id: {tour_id}, user_id: {user_id}")

        conn.commit()

        # 업데이트 후 사용자 장소 데이터 조회
        sql = "SELECT colorcode, place, count FROM user_place WHERE user_id = %s AND colorcode IS NOT NULL"
        cursor.execute(sql, (user_id,))
        user_place_data = cursor.fetchall()

    if user_place_data:
        result_data = [
            {
                "colorcode": row[0],
                "place": row[1],
                "visitedCnt": row[2]
            } for row in user_place_data
        ]
        return jsonify(result_data)
    else:
        return jsonify({"message": "여행기록이 없음"})
    
class SSLAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1')  # Adjust security level
        kwargs['ssl_context'] = context
        return super(SSLAdapter, self).init_poolmanager(*args, **kwargs)  

# 탈퇴 처리
@app.route("/resign", methods=['POST'])
def resign():
    message = request.data.decode('utf-8')
    data = json.loads(message)
    user_id = data.get('user_id')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT nickname FROM users WHERE id = %s", (user_id,))
        nickname = cursor.fetchone()

        # 사용자 관련 데이터 삭제
        cursor.execute("DELETE FROM invite WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM invite WHERE nickname = %s", (nickname,))
        cursor.execute("DELETE FROM schedules WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM tour WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM team_members WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM user_place WHERE user_id = %s", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        
        conn.commit()

    return "탈퇴 완료"

# 캠핑 일정 짜기
@app.route('/camping', methods=['POST'])
def fetch_camping_sites():
    data = request.json
    destination = data.get('destination')
    
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 캠핑 장소 조회
        sql = "SELECT longitude, latitude FROM camping_place WHERE city = %s"
        cursor.execute(sql, (destination,))
        coords = cursor.fetchone()  # 튜플 형태로 반환됨

    if not coords:
        return jsonify({"error": "위치를 찾을 수 없습니다"}), 404

    lat = coords[1]  # 위도
    lon = coords[0]  # 경도

    session = requests.Session()
    session.mount('https://', SSLAdapter())

    url = "https://apis.data.go.kr/B551011/GoCamping/locationBasedList"
    params = {
        "numOfRows": "3",
        "pageNo": "1",
        "MobileOS": "AND",
        "MobileApp": "TourRand",
        "serviceKey": camping_service_key,
        "mapX": lon,  # 경도
        "mapY": lat,  # 위도
        "radius": "10000"
    }

    headers = {
        "accept": "*/*"
    }

    response = session.get(url, params=params, headers=headers)

    # 상태 코드와 응답 내용 출력 (디버깅용)
    print("Status Code:", response.status_code)
    print("Response Content:", response.content)
    print("Response Headers:", response.headers)

    if response.headers['Content-Type'].startswith('application/xml'):
        try:
            root = ET.fromstring(response.content)
            items = []

            for item in root.findall('.//item'):
                facltNm = item.find('facltNm').text if item.find('facltNm') is not None else "N/A"
                addr1 = item.find('addr1').text if item.find('addr1') is not None else "N/A"
                addr2 = item.find('addr2').text if item.find('addr2') is not None else "N/A"

                # Get latitude and longitude for the address
                address = f"{addr1} {addr2}"
                longitude, latitude = get_lat_long(address)

                items.append({
                    "address": f"{addr1} {addr2}",
                    "day": 1,
                    "location": facltNm,
                    "longitude": latitude,
                    "latitude": longitude
                })
            
            if not items:
                return jsonify({"message": "No camping sites found"}), 404

            # Select a random camping site from the list
            random_item = random.choice(items)

            # Create two entries for the selected item with different days
            response_items = [
                {**random_item, "day": 1},
                {**random_item, "day": 2}
            ]

            return jsonify(response_items)
        except ET.ParseError as e:
            return jsonify({"error": "Failed to parse XML", "details": str(e)}), 500
    else:
        return jsonify({"error": "Unexpected content type", "response": response.text}), response.status_code

# 세부 지역 검색 가능 지역
detailed_region_codes = {
    "인천": "2",
    "강원": "32",
    "경기": "31"
}

# 지역코드 조회 API 호출
def get_region_codes():
    url = "http://apis.data.go.kr/B551011/GreenTourService1/areaCode1"
    params = {
        "serviceKey": eco_service_key,
        "numOfRows": 100,
        "pageNo": 1,
        "MobileOS": "ETC",
        "MobileApp": "AppTest"
    }
    response = requests.get(url, params=params)

    # XML 파싱
    try:
        root = ET.fromstring(response.text)
    except ET.ParseError as e:
        return {}

    region_codes = {}
    for item in root.findall("./body/items/item"):
        code = item.find("code").text
        name = item.find("name").text
        if name not in detailed_region_codes:
            region_codes[name] = code  # 세부 지역이 아닌 일반 지역만 저장
    return region_codes

# 지역 기반 생태관광정보 조회
def get_ecotourism_data(region_code):
    url = "http://apis.data.go.kr/B551011/GreenTourService1/areaBasedList1"
    all_items = []
    page_no = 1
    
    while True:
        params = {
            "numOfRows": 1000,
            "pageNo": page_no,
            "MobileOS": "ETC",
            "MobileApp": "AppTest",
            "_type": "json",
            "areaCode": region_code,
            "serviceKey": eco_service_key
        }
        response = requests.get(url, params=params)
        
        try:
            data = response.json()
        except ValueError:
            break

        # API 응답 데이터 구조 확인 및 오류 메시지 출력 제거
        if "response" in data and "body" in data["response"] and "items" in data["response"]["body"]:
            items = data["response"]["body"]["items"]

            if isinstance(items, dict) and "item" in items:
                items_list = items["item"]

                if isinstance(items_list, list):
                    if items_list:
                        all_items.extend(items_list)
                        page_no += 1
                    else:
                        break
            elif items is None:
                break
            else:
                break
        else:
            break
    
    return all_items

# 특정 세부 지역의 데이터만 필터링
def filter_by_subregion(items, subregion_name):
    filtered_items = []

    for item in items:
        addr = item.get("addr", "")
        if subregion_name in addr:
            filtered_items.append(item)

    return filtered_items

# 중복 제거 함수
def remove_duplicates(items):
    seen = set()
    unique_items = []

    for item in items:
        addr = item.get("addr", "")
        if addr not in seen:
            seen.add(addr)
            unique_items.append(item)
    
    return unique_items

# 병렬 처리로 모든 지역의 데이터 수집
def fetch_all_data(region_codes, detailed_region_codes):
    all_items = []

    # 병렬 처리의 스레드 풀 생성
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []

        # 일반 지역 데이터 수집
        for region_code in region_codes.values():
            futures.append(executor.submit(get_ecotourism_data, region_code))

        # 세부 지역 데이터 수집
        for detailed_code in detailed_region_codes.values():
            futures.append(executor.submit(get_ecotourism_data, detailed_code))

        # 모든 Future 객체의 결과 수집
        for future in as_completed(futures):
            try:
                result = future.result()
                all_items.extend(result)
            except Exception as e:
                print(f"데이터 수집 중 오류 발생: {e}")

    return remove_duplicates(all_items)

# 생태 위도 경도 알아내는 함수
def get_lat_long(address):
    api_key = map_api_key  # 구글 맵 API 키
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={address}&key={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if data['status'] == 'OK':
            location = data['results'][0]['geometry']['location']
            return location['lat'], location['lng']
        else:
            print(f"Error fetching location: {data['status']}")
            return None, None
    except Exception as e:
        print(f"Error during API request: {e}")
        return None, None

# 생태 일정 짜기
@app.route('/ecotourism', methods=['POST'])
def ecotourism():
    # 사용자로부터 요청받은 JSON 데이터 가져오기
    message = request.data.decode('utf-8')
    data = json.loads(message)
    
    destination = data.get('destination')  # 지역 검색어
    date_str = data.get('day')  # 일정 개수

    date = int(date_str)  # 일정 개수
    count = generate_itinerary(date)
    
    # 지역코드 조회
    region_codes = get_region_codes()

    # 전체 데이터 수집
    all_items = fetch_all_data(region_codes, detailed_region_codes)

    # 입력받은 지역에 해당하는 데이터 필터링
    filtered_items = filter_by_subregion(all_items, destination)

    # 특정 지역에 따라 선택할 장소 개수 설정
    if destination in ["안산", "파주", "포천", "정선", "태백", "서울", "인천", "대전", "대구", "울산"]:
        ecotourism_count = 2  # 2개 장소
    elif destination in ["광주", "안양", "의왕", "시흥", "가평", "남양주", "연천", "평창", "속초", "고성", "원주", "양구", "강릉", "홍천", "삼척"]:
        ecotourism_count = 1  # 1개 장소
    else:
        ecotourism_count = 0  # 기본값

    selected_places = []
    if filtered_items:
        # 랜덤으로 ecotourism_count 개수만큼 장소 선택
        random_filtered_items = random.sample(filtered_items, min(ecotourism_count, len(filtered_items)))
        
        for item in random_filtered_items:
            full_address = item.get("addr", "").replace("NULL", "").strip()
            lat, lng = get_lat_long(full_address)  # 위도와 경도 가져오기
            
            selected_places.append({
                "place_name": item.get("title", "Unnamed Place"),
                "full_address": full_address,
                "longitude": lng if lng is not None else 0,
                "latitude": lat if lat is not None else 0
            })

    print("선택된 생태관광지:", selected_places)
    
    # 나머지 장소 필요 개수
    remaining_count = sum(count) - len(selected_places)
    places_list = selected_places[:]
     
    # 생태관광지 외 다른 테마의 장소 조회
    if remaining_count > 0:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            sql_other = """
                SELECT place_name, full_address
                FROM place
                WHERE sec_place = %s AND
                      (theme1 = %s OR theme2 = %s OR theme2 = %s) AND
                      full_address IS NOT NULL
                ORDER BY RAND()
                LIMIT %s
            """
            cursor.execute(sql_other, (destination, "자연", "힐링", "역사" , remaining_count))
            other_places = cursor.fetchall()

            for row in other_places:
                lat, lng = get_lat_long(row[1])
                places_list.append({
                    "place_name": row[0],
                    "full_address": row[1].replace("NULL", "").strip(),
                    "longitude": lng,
                    "latitude": lat
                })
    
    print("최종 장소 수:", len(places_list))  # 로그 추가
    
    # 일정 JSON 생성
    itinerary_json = generate_and_chat(places_list, date, cursor, destination, "힐링", remaining_count, count)
    print("gpt가 생성한 일정 :", itinerary_json)
    
    if (len(itinerary_json) == 0):
        return "장소부족"
    
    return jsonify(itinerary_json) if places_list else jsonify({"message": f"{destination} 지역에 대한 데이터가 없습니다."})

@app.route("/youtube", methods=['POST'])
def get_random_youtube_video():
    # 요청 본문에서 theme 추출
    data = request.get_json()
    theme = data.get('theme', '')
    
    if not theme:
        return jsonify({"error": "테마가 제공되지 않았습니다."}), 400

    # 검색어를 생성 (예: "힐링 할 때 좋은 노래")
    search_query = f"{theme} 할 때 좋은 노래"

    # 유튜브 API URL 설정
    base_url = "https://www.googleapis.com/youtube/v3/search"
    
    # 요청 매개변수 설정
    params = {
        "part": "snippet",
        "q": search_query,
        "key": youtube_api_key,
        "maxResults": 10,  # 가져올 동영상 수
        "type": "video"
    }

    # 요청 보내기
    response = requests.get(base_url, params=params)

    # 응답 결과 확인
    if response.status_code == 200:
        videos = response.json().get('items', [])
        
        if videos:
            # 리스트에서 랜덤하게 하나의 동영상을 선택
            random_video = random.choice(videos)
            
            video_title = random_video['snippet']['title']
            video_id = random_video['id']['videoId']
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            return jsonify({
                "title": video_title,
                "url": video_url
            })
        else:
            return jsonify({"error": "검색된 동영상이 없습니다."}), 404
    else:
        return jsonify({"error": f"API 요청에 실패했습니다. 상태 코드: {response.status_code}"}), response.status_code
       
# 날씨 위치 좌표 받아오기
def get_location_from_db(location_name):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT nx, ny FROM coordinate WHERE place_name = %s", (location_name,))
            result = cursor.fetchone()

            if result:
                return {"nx": result[0], "ny": result[1]}
            else:
                return None

    except pymysql.MySQLError as err:
        print(f"Database error: {err}")
        return None

# 기상청 API에서 날씨 정보 가져오기
def get_kma_weather(location_name):
    base_url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
    now = datetime.now()
    base_date = now.strftime("%Y%m%d")
    
    forecast_times = ['0200', '0500', '0800', '1100', '1400', '1700', '2000', '2300']
    current_hour_min = now.hour * 100 + now.minute
    closest_time = None

    for time_str in forecast_times:
        time_int = int(time_str)
        if current_hour_min >= time_int:
            closest_time = time_str
        else:
            break

    if closest_time is None:
        closest_time = forecast_times[-1]
        base_date = (now - timedelta(days=1)).strftime("%Y%m%d")
    base_time = closest_time

    # DB에서 해당 위치의 좌표 정보를 가져옴
    location_info = get_location_from_db(location_name)
    if location_info:
        nx = location_info["nx"]
        ny = location_info["ny"]
    else:
        return {"error": "Invalid location name"}

    # 기상청 API 요청 매개변수 설정
    params = {
        'serviceKey': weather_service_key,
        'pageNo': '1',
        'numOfRows': '100',
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': str(nx),
        'ny': str(ny)
    }

    # 날씨 정보 요청
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        weather_data = response.json()
        
        if "response" in weather_data and "body" in weather_data["response"]:
            items = weather_data["response"]["body"]["items"]["item"]
            weather_info = {}
            
            # 날씨 데이터를 카테고리별로 추출
            for item in items:
                category = item['category']
                value = item['fcstValue']
                weather_info[category] = value
            
            # 하늘 상태(SKY) 값 변환
            sky_status = ""
            if weather_info.get('SKY') == '1':
                sky_status = "맑음"
            elif weather_info.get('SKY') == '2':
                sky_status = "구름 조금"
            elif weather_info.get('SKY') == '3':
                sky_status = "구름 많음"
            elif weather_info.get('SKY') == '4':
                sky_status = "흐림"

            # 최종 결과 변환
            result = {
                "지역": location_name,
                "기온(TMP)": f"{int(weather_info.get('TMP', '0'))}℃",
                "강수 형태(PTY)": "없음" if weather_info.get('PTY') == '0' else "비" if weather_info.get('PTY') == '1' else "눈",
                "강수 확률(POP)": f"{weather_info.get('POP', '0')}%",
                "풍속(WSD)": f"{float(weather_info.get('WSD', '0')):.1f}m/s",
                "하늘 상태(SKY)": sky_status,
                "오늘의 옷차림 추천": get_clothing_recommendation(
                    int(weather_info.get('TMP', '0')),
                    weather_info.get('PTY', '0'),
                    float(weather_info.get('WSD', '0'))
                )
            }
            
            return result
        else:
            return {"error": "Failed to retrieve weather data"}
    
    except requests.RequestException as e:
        return {"error": f"Request error: {e}"}

def get_clothing_recommendation(temperature, precipitation, wind_speed):
    recommendation = ""

    # 온도에 따른 기본 옷차림 추천
    if temperature >= 30:
        recommendation = "민소매, 반팔 티셔츠, 반바지"
    elif 25 <= temperature < 30:
        recommendation = "반팔 티셔츠, 얇은 셔츠, 반바지"
    elif 20 <= temperature < 25:
        recommendation = "긴팔 셔츠, 얇은 스웨터, 청바지, 면바지"
    elif 15 <= temperature < 20:
        recommendation = "가벼운 자켓, 긴팔 티셔츠, 니트, 청바지"
    elif 10 <= temperature < 15:
        recommendation = "가을 자켓, 얇은 코트, 니트, 긴바지"
    elif 5 <= temperature < 10:
        recommendation = "두꺼운 자켓, 코트, 스웨터, 기모바지"
    elif 0 <= temperature < 5:
        recommendation = "패딩, 두꺼운 코트, 히트텍, 기모 옷"
    else:
        recommendation = "패딩, 두꺼운 코트, 목도리, 장갑, 기모 옷"

    # 강수 형태에 따른 우산 챙기기 추천
    if precipitation == '1' or precipitation == '2':
        recommendation += " 우산."

    # 풍속에 따른 바람막이 추천
    if wind_speed >= 8.0:
        recommendation += " 바람막이"

    return recommendation

@app.route('/weather', methods=['POST'])
def weather():
    message = request.data.decode('utf-8')
    data = json.loads(message)

    user_id = data.get('user_id')
    tour_id = data.get('tour_id')
    
    if not user_id or not tour_id:
        return jsonify({"error": "user_id와 tour_id는 필수입니다."}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()
        sql = "SELECT place FROM user_place WHERE user_id = %s AND tour_id = %s"
        cursor.execute(sql, (user_id, tour_id))
        result = cursor.fetchone()
    
    if not result:
        return jsonify({"error": "해당 사용자의 장소 정보를 찾을 수 없습니다."}), 404
    
    location_name = result[0]
    weather_info = get_kma_weather(location_name)
    
    if isinstance(weather_info, dict):
        return jsonify(weather_info)
    else:
        return jsonify({"error": "Unexpected error occurred"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    # 서버가 정상 동작하는 경우 200 상태 코드를 반환
    return jsonify({"status": "UP"}), 200

# 룰렛 돌리기
@app.route('/roulette_save', methods=['POST'])
def save_roulette_result():
    message = request.data.decode('utf-8')
    data = json.loads(message)
    
    tour_id = data.get('tour_id')
    
    if not tour_id:
        return jsonify({"error": "tour_id는 필수입니다."}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM team_members WHERE tour_id = %s", (tour_id,))
        user_ids = cursor.fetchall()
    
    if not user_ids:
        return jsonify({"error": "해당 투어에 사용자가 없습니다."}), 404
    
    random_user_id = random.choice(user_ids)[0]
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nickname FROM users WHERE id = %s", (random_user_id,))
        nickname = cursor.fetchone()
        
        cursor.execute("""
            INSERT INTO roulette_results (user_id, tour_id, count) 
            VALUES (%s, %s, 1) 
            ON DUPLICATE KEY UPDATE count = count + 1
        """, (random_user_id, tour_id))
        conn.commit()

    return jsonify({"message": "랜덤 유저 선택 완료", "nickname": nickname[0]})

# 룰렛 결과 조회
@app.route('/roulette_results', methods=['POST'])
def get_roulette_results():
    message = request.data.decode('utf-8')
    data = json.loads(message)

    tour_id = data.get('tour_id')

    if not tour_id:
        return jsonify({"error": "tour_id는 필수입니다."}), 400

    with get_db_connection() as conn:
        cursor = conn.cursor()
        sql = """
        SELECT rr.user_id, rr.count 
        FROM roulette_results rr 
        WHERE rr.tour_id = %s
        """
        cursor.execute(sql, (tour_id,))
        results = cursor.fetchall()
    
    if not results:
        return jsonify({"message": "저장된 결과가 없습니다."}), 200

    user_ids = [row[0] for row in results]
    user_ids_placeholder = ', '.join(['%s'] * len(user_ids))  # SQL 쿼리에서 사용할 플레이스홀더 생성

    with get_db_connection() as conn:
        cursor = conn.cursor()
        sql_users = f"""
        SELECT id, nickname 
        FROM users 
        WHERE id IN ({user_ids_placeholder})
        """
        cursor.execute(sql_users, tuple(user_ids))
        user_results = cursor.fetchall()

    user_nicknames = {row[0]: row[1] for row in user_results}
    
    roulette_results = [{"nickname": user_nicknames.get(user_id, "닉네임 없음"), "count": count} 
                        for user_id, count in results]

    return jsonify({"results": roulette_results})

#고정 서버
@app.route("/server_info")
def server_info():
    data = {'host': MY_IP_ADDRESS, 'port':'5000'}
    return jsonify(data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True) 
