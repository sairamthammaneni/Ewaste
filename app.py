import os
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Firebase setup
key_path = os.path.join(os.path.dirname(__file__), "serviceAccountKey.json")
cred = credentials.Certificate(key_path)
firebase_admin.initialize_app(cred)
db = firestore.client()

EARN_RATE = 190  # Rupees per KG

@app.route('/')
def index():
    return redirect(url_for('login_register'))

@app.route('/login', methods=['GET', 'POST'])
def login_register():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']

        user_ref = db.collection('users').where('email', '==', email).limit(1)
        docs = list(user_ref.stream())

        if docs:
            # Existing user – check password
            user_data = docs[0].to_dict()
            hashed_pw = user_data['password']

            if check_password_hash(hashed_pw, password):
                session['user_email'] = email
                flash("Logged in successfully.")
                return redirect(url_for('dashboard'))
            else:
                flash("Incorrect password.")
        else:
            # New user – register
            hashed_pw = generate_password_hash(password)
            db.collection('users').add({
                'email': email,
                'password': hashed_pw,
                'ewaste_given_kg': 0,
                'money_received': 0
            })
            session['user_email'] = email
            flash("Welcome! Account created.")
            return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_email' not in session:
        return redirect(url_for('login_register'))

    email = session['user_email']
    user_ref = db.collection('users').where('email', '==', email).limit(1)
    docs = list(user_ref.stream())

    if docs:
        user_data = docs[0].to_dict()
        return render_template('dashboard.html', user=user_data)
    else:
        flash("User data not found.")
        return redirect(url_for('login_register'))

@app.route('/contribute', methods=['GET', 'POST'])
def contribute():
    if 'user_email' not in session:
        return redirect(url_for('login_register'))

    email = session['user_email']
    user_ref = db.collection('users').where('email', '==', email).limit(1)
    docs = list(user_ref.stream())

    if not docs:
        flash("User not found.")
        return redirect(url_for('dashboard'))

    doc = docs[0]
    doc_id = doc.id
    user_data = doc.to_dict()

    if request.method == 'POST':
        try:
            ewaste_input = float(request.form['ewaste_kg'])
            new_ewaste = user_data['ewaste_given_kg'] + ewaste_input
            new_money = user_data['money_received'] + ewaste_input * EARN_RATE

            db.collection('users').document(doc_id).update({
                'ewaste_given_kg': new_ewaste,
                'money_received': new_money
            })

            flash(f"Thanks! ₹{ewaste_input * EARN_RATE} added.")
            return redirect(url_for('dashboard'))

        except Exception as e:
            flash(f"Error: {e}")

    return render_template('contribute.html')

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login_register'))

if __name__ == '__main__':
    app.run(debug=True)