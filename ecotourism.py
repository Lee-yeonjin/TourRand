import requests
import xml.etree.ElementTree as ET
import sys
import csv

# 공공데이터포털에서 발급받은 인증키
service_key = os.getenv('eco_service_key')

# 지역코드 조회 API 호출
def get_region_codes():
    url = "http://apis.data.go.kr/B551011/GreenTourService1/areaCode1"
    params = {
        "serviceKey": service_key,
        "numOfRows": 10,
        "pageNo": 1,
        "MobileOS": "ETC",
        "MobileApp": "AppTest"
    }
    response = requests.get(url, params=params)
    root = ET.fromstring(response.text)
    region_codes = {}
    for item in root.findall("./body/items/item"):
        code = item.find("code").text
        name = item.find("name").text
        region_codes[code] = name
    return region_codes

# 지역 기반 생태관광정보 조회
def get_all_ecotourism_data():
    url = "http://apis.data.go.kr/B551011/GreenTourService1/areaBasedList1"
    all_items = []
    region_codes = get_region_codes()
    for region_code in region_codes:
        page_no = 1
        while True:
            params = {
                "numOfRows": 10,
                "pageNo": page_no, 
                "MobileOS": "ETC",
                "MobileApp": "AppTest",
                "_type": "json",
                "areaCode": region_code,
                "serviceKey": service_key
            }
            response = requests.get(url, params=params)
            data = response.json()
            
            if "response" in data and "body" in data["response"] and "items" in data["response"]["body"] and "item" in data["response"]["body"]["items"]:
                items = data["response"]["body"]["items"]["item"]
                all_items.extend(items)
                if len(items) < 10:
                    break
                page_no += 1
            else:
                break
    return all_items

def main():
    all_items = get_all_ecotourism_data()
    
    # CSV 파일 저장
    with open("ecotourism_data2.csv", "w", newline="", encoding="utf-8-sig") as csvfile:
        fieldnames = list(all_items[0].keys())
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in all_items:
            writer.writerow(item)
    
    print("ecotourism_data2.csv 파일이 생성되었습니다.")

if __name__ == "__main__":
    main()
