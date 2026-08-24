import os

os.environ.setdefault('FLASK_CONFIG', 'production')
os.environ.setdefault('VERCEL', '1')

from app import create_app

app = create_app('production')
