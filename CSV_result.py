import pandas as pd
import tensorflow as tf
import joblib

# 모델과 스케일러 불러오기
model = tf.keras.models.load_model('BaseFile/csvmodel.h5')
scaler = joblib.load('BaseFile/scaler.joblib')

# 입력 데이터 예측 함수
def predicted_stroke(user_data):
    # 입력 데이터를 DataFrame으로 변환
    user_df = pd.DataFrame([user_data])
    
    # 입력 데이터를 스케일링
    scaled_user_data = scaler.transform(user_df)
    
    # 불러온 모델로 예측 수행
    prediction_proba = model.predict(scaled_user_data)[0][0]
    
    # 뇌졸중 발생 가능성 백분율로 변환
    probability_percentage = prediction_proba * 100
    
    return probability_percentage
