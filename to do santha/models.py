from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.name = user_data.get('name')
        self.email = user_data.get('email')
        self.bio = user_data.get('bio', '')
        self.profile_pic = user_data.get('profile_pic', '')
