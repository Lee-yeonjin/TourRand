import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import SVC
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from imblearn.over_sampling import SMOTE
from collections import Counter

# 엑셀 파일에서 데이터 불러오기
file_path = 'C:/Users/duswls/Desktop/tourrand/sampledata3.xlsx'  # 엑셀 파일 경로를 지정하세요
data = pd.read_excel(file_path)

data = data.dropna()

# TF-IDF 벡터화
vectorizer = TfidfVectorizer(max_df=0.8, min_df=2, ngram_range=(1, 2))
X_tfidf = vectorizer.fit_transform(data['description'])

# 데이터셋 분리
X_train, X_test, y_train_theme, y_test_theme = train_test_split(X_tfidf, data['theme'], test_size=0.2, random_state=42)
_, _, y_train_theme2, y_test_theme2 = train_test_split(X_tfidf, data['theme2'], test_size=0.2, random_state=42)


# 클래스당 샘플 수 확인
theme_class_counts = Counter(y_train_theme)
theme2_class_counts = Counter(y_train_theme2)

def get_k_neighbors(class_counts):
    min_samples = min(class_counts.values())
    return max(1, min_samples - 1)

smote_theme_k_neighbors = get_k_neighbors(theme_class_counts)
smote_theme2_k_neighbors = get_k_neighbors(theme2_class_counts)

# SMOTE를 사용하여 클래스 불균형 해결
def apply_smote(X, y, k_neighbors):
    if min(Counter(y).values()) > k_neighbors:
        smote = SMOTE(k_neighbors=k_neighbors, random_state=42)
        return smote.fit_resample(X, y)
    else:
        #print(f"Skipping SMOTE for {k_neighbors} neighbors due to insufficient class samples.")
        return X, y

X_train_resampled_theme, y_train_theme_resampled = apply_smote(X_train, y_train_theme, smote_theme_k_neighbors)
X_train_resampled_theme2, y_train_theme2_resampled = apply_smote(X_train, y_train_theme2, smote_theme2_k_neighbors)

# SVM 모델 학습
svm_model_theme = SVC(decision_function_shape='ovr', kernel='linear', C=10, class_weight='balanced')
svm_model_theme.fit(X_train_resampled_theme, y_train_theme_resampled)

svm_model_theme2 = SVC(decision_function_shape='ovr', kernel='linear', C=10 , class_weight='balanced')
svm_model_theme2.fit(X_train_resampled_theme2, y_train_theme2_resampled)

# 모델 평가
y_pred_theme = svm_model_theme.predict(X_test)
y_pred_theme2 = svm_model_theme2.predict(X_test)

# 새로운 데이터 예측 예제
new_descriptions = [
    "경기도 용인시 처인구 포곡읍 에버랜드로 199에 위치한 테마파크. 현재까지 대한민국 최대 규모의 놀이공원 및 동물원이 있다.",
    "주랜드 + 플라워랜드 + 조이랜드”를 복합적으로 구성하여 온가족이 함께 즐길 수 있는 테마공원 ."
]

new_X_tfidf = vectorizer.transform(new_descriptions)

new_y_pred_theme = svm_model_theme.predict(new_X_tfidf)
new_y_pred_theme2 = svm_model_theme2.predict(new_X_tfidf)

print("새로운 데이터 예측 결과:")
for i, (theme, theme2) in enumerate(zip(new_y_pred_theme, new_y_pred_theme2)):
    print(f"새로운 데이터 {i+1}: {theme}, {theme2}")

joblib.dump(svm_model_theme, 'svm_model_theme.pkl')
joblib.dump(svm_model_theme2, 'svm_model_theme2.pkl')

# TF-IDF 벡터라이저 저장
joblib.dump(vectorizer, 'tfidf_vectorizer.pkl')
