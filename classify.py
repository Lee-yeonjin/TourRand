import pandas as pd
import requests

# 엑셀 파일 읽기
df = pd.read_csv('C://Users//duswls//Desktop//tourrand//search.xlsx', encoding='utf-8')

# 위도와 경도 정보 가져오기
for i, row in df.iterrows():
    address = row['addr']
    url = f'https://dapi.kakao.com/v2/local/search/address.json?query={address}'
    headers = {'Authorization': 'KakaoAK YOUR_API_KEY'}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if data['documents']:
            latitude = data['documents'][0]['y']
            longitude = data['documents'][0]['x']
            df.at[i, '경도'] = longitude
            df.at[i, '위도'] = latitude
        else:
            df.at[i, '경도'] = None
            df.at[i, '위도'] = None
    else:
        df.at[i, '경도'] = None
        df.at[i, '위도'] = None

# 엑셀 파일에 저장
df.to_excel('search_with_coordinates.xlsx', index=False)
