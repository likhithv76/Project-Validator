from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
file_path = os.path.join(base_dir, "todo.db")

app = Flask(
    __name__,
    template_folder=os.path.join(base_dir, "templates"),
    static_folder=os.path.join(base_dir, "static"),
)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+file_path
db = SQLAlchemy(app)

from app import routes

with app.app_context():
    db.create_all()