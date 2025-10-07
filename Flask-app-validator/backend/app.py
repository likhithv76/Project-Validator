from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'validation_logs.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{DB_PATH}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class ValidationRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(100), nullable=False)
    project_name = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(10), nullable=False)
    log_file = db.Column(db.String(300), nullable=False)
    errors = db.Column(db.Text)
    warnings = db.Column(db.Text)

    def as_dict(self):
        return {
            "id": self.id,
            "student_id": self.student_id,
            "project_name": self.project_name,
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "log_file": self.log_file,
            "errors": self.errors,
            "warnings": self.warnings,
        }


with app.app_context():
    db.create_all()


@app.route("/submit", methods=["POST"])
def submit():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing data"}), 400

    record = ValidationRecord(
        student_id=data["student_id"],
        project_name=data["project_name"],
        status=data["status"],
        log_file=data["log_file"],
        errors="\n".join(data.get("errors", [])),
        warnings="\n".join(data.get("warnings", [])),
    )
    db.session.add(record)
    db.session.commit()
    return jsonify({"message": "Record saved", "id": record.id}), 200


@app.route("/records", methods=["GET"])
def get_records():
    records = ValidationRecord.query.order_by(ValidationRecord.timestamp.desc()).all()
    return jsonify([r.as_dict() for r in records])


@app.route("/records/<student_id>", methods=["GET"])
def get_by_student(student_id):
    records = ValidationRecord.query.filter_by(student_id=student_id).order_by(ValidationRecord.timestamp.desc()).all()
    return jsonify([r.as_dict() for r in records])


if __name__ == "__main__":
    app.run(debug=True, port=6000)
