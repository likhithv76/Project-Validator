from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os

app = Flask(__name__)
app.secret_key = 'test_secret_key'

# Sample data
users = [
    {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
    {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com'}
]

@app.route('/')
def index():
    return render_template('index.html', users=users)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        flash(f'Thank you {name}! Your message has been sent.', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')

@app.route('/api/users')
def api_users():
    return jsonify(users)

@app.route('/api/users/<int:user_id>')
def api_user(user_id):
    user = next((u for u in users if u['id'] == user_id), None)
    if user:
        return jsonify(user)
    return jsonify({'error': 'User not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
