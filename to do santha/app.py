from flask import Flask, render_template, request, redirect, url_for, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from models import User

import os
from werkzeug.utils import secure_filename



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__)
app.secret_key = 'supersecret'

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create uploads folder if not exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Mongo setup
client = MongoClient("mongodb://localhost:27017/")
db = client["todo_db"]
users_collection = db["users"]
tasks_collection = db["tasks"]

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

@app.route('/')
@login_required
def index():
    tasks = list(tasks_collection.find({'user_id': current_user.id}))
    return render_template('index.html', tasks=tasks)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        if users_collection.find_one({'email': email}):
            return "Email already exists. Try login."

        hashed_pw = generate_password_hash(password)
        user_id = users_collection.insert_one({
            'name': name,
            'email': email,
            'password': hashed_pw,
            'bio': '',
            'profile_pic': 'https://ui-avatars.com/api/?name=' + '+'.join(name.split())
        }).inserted_id

        user = users_collection.find_one({'_id': user_id})
        login_user(User(user))
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = users_collection.find_one({'email': email})

        if user and check_password_hash(user['password'], password):
            login_user(User(user))
            return redirect(url_for('index'))
        return "Invalid credentials"
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add', methods=['POST'])
@login_required
def add():
    task = {
        'content': request.form['content'],
        'date': request.form['date'],
        'time': request.form['time'],
        'priority': request.form['priority'],
        'done': False,
        'user_id': current_user.id
    }
    tasks_collection.insert_one(task)
    return redirect(url_for('index'))

@app.route('/delete/<task_id>')
@login_required
def delete(task_id):
    tasks_collection.delete_one({'_id': ObjectId(task_id), 'user_id': current_user.id})
    return redirect(url_for('index'))

@app.route('/toggle/<task_id>')
@login_required
def toggle(task_id):
    task = tasks_collection.find_one({'_id': ObjectId(task_id), 'user_id': current_user.id})
    tasks_collection.update_one({'_id': ObjectId(task_id)}, {'$set': {'done': not task['done']}})
    return redirect(url_for('index'))

@app.route('/profile')
@login_required
def profile():
    user_data = users_collection.find_one({'_id': ObjectId(current_user.id)})
    pending_count = tasks_collection.count_documents({'user_id': current_user.id, 'done': False})
    return render_template('profile.html', user=user_data, pending=pending_count)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = users_collection.find_one({'_id': ObjectId(current_user.id)})

    if request.method == 'POST':
        name = request.form['name']
        bio = request.form['bio']
        update_data = {'name': name, 'bio': bio}

        file = request.files.get('profile_pic')
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            update_data['profile_pic'] = f"/static/uploads/{filename}"

        users_collection.update_one({'_id': ObjectId(current_user.id)}, {'$set': update_data})
        return redirect(url_for('profile'))

    return render_template('edit_profile.html', user=user)

if __name__ == '__main__':
    app.run(debug=True)