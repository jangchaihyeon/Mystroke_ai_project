import numpy as np
import cv2
from keras.models import load_model

# 모델 로드
model = load_model('BaseFile/cnn_model.h5')

def preprocess_image_for_cnn(image_path):
    """이미지를 CNN 모델을 위해 전처리"""
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"이미지를 불러올 수 없습니다: {image_path}")
    image = cv2.resize(image, (128, 128))
    image = image / 255.0  # [0, 1] 범위로 정규화
    return np.expand_dims(image, axis=0)

def predict_stroke(image_path):
    """이미지 경로를 받아 뇌졸중 예측을 수행"""
    processed_image = preprocess_image_for_cnn(image_path)
    prediction_prob = model.predict(processed_image)
    
    prob_stroke = prediction_prob[0][0]
    prob_normal = 1 - prob_stroke
    
    if prob_stroke > prob_normal:
        confidence = prob_stroke * 100
        result = '뇌졸중'
    else:
        confidence = prob_normal * 100
        result = '정상'
    
    return result, confidence
