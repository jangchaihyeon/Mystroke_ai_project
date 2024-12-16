from flask import Flask, request, redirect, url_for, render_template, flash, send_from_directory, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import os
from werkzeug.utils import secure_filename
from CNN_result import predict_stroke  # result.py에서 predict_stroke 함수 가져오기
from CSV_result import predicted_stroke
import json
from threading import Timer
from flask_cors import CORS

# Flask 설정
app = Flask(__name__)
CORS(app)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'

# 데이터베이스 설정
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# 데이터베이스 모델 정의
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    weight = db.Column(db.Integer, nullable=True)
    hypertension = db.Column(db.Integer, nullable=True, default=0)  # 고혈압 여부
    heart_disease = db.Column(db.Integer, nullable=True, default=0)  # 심장병 여부

# Flask-Login 설정
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 업로드 폴더 설정
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 허용된 파일 확장자 설정
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 업로드 폴더 생성 (존재하지 않을 경우)
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def delete_file_later(file_path, delay):
    def delete_file():
        try:
            os.remove(file_path)
            print(f'File {file_path} deleted successfully (Backup delete)')
        except FileNotFoundError:
            print(f'File {file_path} already deleted.')
        except Exception as e:
            print(f'Error deleting file {file_path}: {e}')
    
    timer = Timer(delay, delete_file)
    timer.start()

@app.route('/')
def index():
    return render_template('index.html', logged_in=current_user.is_authenticated)

@app.route('/upload')
@login_required
def upload():
    return render_template('upload.html')

@app.route('/upload_file', methods=['POST'])
@login_required
def upload_file():
    if 'userPhoto' not in request.files:
        flash('파일이 선택되지 않았습니다.', 'error')
        return redirect(url_for('upload'))
    
    file = request.files['userPhoto']
    
    if file.filename == '':
        flash('선택된 파일이 없습니다.', 'error')
        return redirect(url_for('upload'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # 저장된 파일 경로를 predict_stroke 함수에 전달
            result, confidence = predict_stroke(filepath)

            # 이미지 30초 후 삭제 예약
            delete_file_later(filepath, 30)  # 30초 후 이미지 파일 삭제
            print("30초 후 uploads 파일이 초기화됩니다.")

            # 결과를 결과 페이지로 전달
            return render_template('result.html', result=result, confidence=confidence, filename=filename)
        except Exception as e:
            flash(f'처리 중 오류 발생: {str(e)}', 'error')
            return redirect(url_for('upload'))
    else:
        flash('허용되지 않는 파일 형식입니다.', 'error')
        return redirect(url_for('upload'))

    
@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/result')
def result():
    # result.html에 예측 결과랑 확신하는 확률 반환
    return render_template('result.html', result='', confidence='')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # 사용자 존재 여부 확인
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('이미 존재하는 사용자입니다.', 'error')
            return redirect(url_for('signup'))
        
        # 사용자 추가
        new_user = User(email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('회원가입이 완료되었습니다!', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            login_user(user)
            flash('로그인 성공!', 'success')
            return redirect(url_for('index'))
        else:
            flash('이메일이나 비밀번호가 잘못되었습니다.', 'error')
            return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/setting', methods=['GET', 'POST'])
@login_required
def setting():
    user = User.query.filter_by(email=current_user.email).first()
    
    if request.method == 'POST':
        # 나이
        user.age = request.form['age']
        # 고혈압 여부
        user.hypertension = int(request.form['hypertension'])  # 1 또는 0으로 변환
        # 심장병 여부
        user.heart_disease = int(request.form['heart_disease'])  # 1 또는 0으로 변환
        # 체중과 키를 가져오기
        weight = float(request.form['weight'])  # 사용자 입력에서 체중 가져오기
        height = float(request.form['height']) / 100  # cm를 m로 변환

        user.weight = weight
        user.height = height * 100  # 데이터베이스에 cm로 저장

        db.session.commit()
        flash('정보가 수정되었습니다.', 'success')
        return redirect(url_for('index'))
        
    return render_template('setting.html', user=user)


''' 새로 추가된 부분 '''

@app.route('/choose')
@login_required
def choose():
    return render_template('choose.html')

@app.route('/input', methods=['GET', 'POST'])
@login_required
def input_data():
    user = User.query.filter_by(email=current_user.email).first()
    
    if request.method == 'POST':
        age = request.form['age']
        hypertension = request.form['blood-pressure-option']  # 고혈압 여부
        heart_disease = request.form['heart-disease-option']  # 심장병 여부
        weight = request.form['weight']  # 체중
        height = request.form['height']  # 키

        # 사용자 데이터로 로딩 페이지로 리다이렉트
        return redirect(url_for('loading', age=age, hypertension=hypertension, heart_disease=heart_disease, weight=weight, height=height))

    return render_template('input.html', user=user)

@app.route('/loading', methods=['GET', 'POST'])
@login_required
def loading():
    if request.method == 'POST':
        # 사용자 입력 정보 가져오기
        age = request.form.get('age', type=int)
        hypertension = request.form.get('hypertension', type=int)
        heart_disease = request.form.get('heart_disease', type=int)
        weight = request.form.get('weight', type=float)
        height = request.form.get('height', type=float)
    else:
        # 사용자 정보가 없을 때 예외 처리 (예를 들어 GET 요청일 때)
        age = request.args.get('age', type=int)
        hypertension = request.args.get('hypertension', type=int)
        heart_disease = request.args.get('heart_disease', type=int)
        weight = request.args.get('weight', type=float)
        height = request.args.get('height', type=float)

    # BMI 계산
    height_m = float(height) / 100  # cm를 m로 변환
    bmi = float(weight) / (height_m ** 2)

    # 예측할 사용자 데이터 준비
    user_data = {
        'age': age,
        'hypertension': hypertension,
        'heart_disease': heart_disease,
        'bmi': bmi
    }

    # 예측 수행
    prediction_proba = predicted_stroke(user_data)

    return render_template('csvresult.html', probability=prediction_proba)

posts_file = 'posts.json'

# 게시물 불러오기 함수
def load_posts():
    if os.path.exists(posts_file):
        with open(posts_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# 게시물 저장 함수
def save_posts(posts):
    with open(posts_file, 'w', encoding='utf-8') as f:
        json.dump(posts, f, ensure_ascii=False, indent=4)

# 게시물 저장용 리스트
posts = load_posts()

# 카테고리 리스트
categories = ['free_talk', 'rehabilitation_reviews', 'others']

# 게시판 메인
@app.route('/post')
@login_required
def post():
    posts = load_posts()
    return render_template('post.html', posts=posts)

# 카테고리 한글 변환용 딕셔너리
category_names = {
    'free_talk': '자유수다',
    'rehabilitation_reviews': '재활후기',
    'others': '기타'
}

# 카테고리별 게시물 보기
@app.route('/view_posts/<string:category>')
@login_required
def view_posts(category):
    posts = load_posts()
    filtered_posts = [post for post in posts if post.get('category') == category]
    category_name = category_names.get(category, '전체 페이지')  # 한글 카테고리 이름 가져오기
    return render_template('post.html', posts=filtered_posts, category=category_name)

# 글 보기
@app.route('/list/<string:category>/<int:post_id>')
@login_required
def list(category, post_id):
    posts = load_posts()
    # 카테고리에 해당하는 게시물 필터링
    filtered_posts = [post for post in posts if post['category'] == category]
    
    # 게시물 ID로 특정 게시물 찾기
    post = next((post for post in filtered_posts if post['id'] == post_id), None)
    
    if post is None:
        return "Post not found", 404
    
    return render_template('list.html', post=post, post_id=post_id)

# 글 삭제
@app.route('/deletepost/<string:category>/<int:post_id>', methods=['POST'])
@login_required
def deletepost(category, post_id):
    global posts  # 전역 posts 리스트를 사용하기 위해 선언
    # 카테고리에 해당하는 게시물 필터링
    filtered_posts = [post for post in posts if post['category'] == category]
    
    # 게시물 찾기
    post_to_delete = next((post for post in filtered_posts if post['id'] == post_id), None)
    
    if post_to_delete is None:
        return "Post not found", 404
    
    # 게시물 삭제
    posts.remove(post_to_delete)
    save_posts(posts)  # 변경된 리스트 저장

    return redirect(url_for('view_posts', category=category))  # 삭제 후 해당 카테고리 페이지로 리다이렉트

# 글 업로드
@app.route('/posting', methods=['GET', 'POST'])
@login_required
def posting():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content'].replace('\n', '<br>')
        category = request.form['category']  # 선택한 카테고리 받기
        post_id = len(posts) + 1  # 새로운 ID 설정
        posts.append({'id': post_id, 'title': title, 'content': content, 'likes': 0, 'category': category})
        save_posts(posts)  # 수정된 리스트 저장
        return redirect(url_for('post'))
    return render_template('posting.html', categories=categories)  # 카테고리 전달

@app.route('/like/<string:category>/<int:post_id>', methods=['POST'])
def like_post(category, post_id):
    posts = load_posts()  # 게시물 데이터 로드

    for post in posts:
        if post['id'] == post_id and post['category'] == category:
            post['likes'] += 1  # 공감 수 증가
            save_posts(posts)  # 업데이트된 데이터 저장
            return jsonify({'likes': post['likes']})  # JSON 응답

    return jsonify({'error': 'Post not found'}), 404


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃 되었습니다.', 'info')
    return redirect(url_for('index'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # 데이터베이스와 테이블을 생성
    app.run(debug=True)
