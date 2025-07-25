# config.py (alternative if you skip .env)
class Config:
    SECRET_KEY = 'your-hardcoded-key-here'  # ⚠️ Not safe for production!
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False