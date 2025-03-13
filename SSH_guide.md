# Raspberry Pi SSH and Flask Login Guide

This guide explains how to SSH into your Raspberry Pi and set up a Flask application with a login page.

## SSH into Raspberry Pi

### Prerequisites
- Raspberry Pi with Ubuntu Server installed
- Raspberry Pi connected to your network
- SSH enabled on the Raspberry Pi

### SSH Connection Steps

1. **Find your Raspberry Pi's IP address**
   - If you've set up mDNS (Avahi), you can use the hostname:
     ```
     ssh admin@charlespi.local
     ```
   - Alternatively, you can use the IP address:
     ```
     ssh admin@192.168.1.132
     ```
     (Replace with your Pi's actual IP address)

2. **Enter your password**
   - When prompted, enter your password (default: griffin2020)

3. **SSH Key Authentication (Optional but Recommended)**
   - Generate an SSH key pair on your local machine:
     ```
     ssh-keygen -t ed25519 -C "your_email@example.com"
     ```
   - Copy your public key to the Raspberry Pi:
     ```
     ssh-copy-id admin@charlespi.local
     ```
   - Now you can SSH without a password

## Setting Up a Flask Login Application

### 1. Install Required Packages

```bash
# Create a virtual environment
mkdir -p ~/flask-app
cd ~/flask-app
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Install required packages
pip install flask flask-httpauth gunicorn
```

### 2. Create the Flask Application

Create a file named `app.py`:

```bash
nano ~/flask-app/app.py
```

Add the following code:

```python
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("/var/log/flask-app.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management
auth = HTTPBasicAuth()

# Authentication
users = {
    "admin": generate_password_hash("griffin2020")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username
    return None

@app.route('/')
@auth.login_required
def home():
    return render_template('index.html', username=auth.current_user())

@app.route('/api/data', methods=['GET'])
@auth.login_required
def get_data():
    # Example API endpoint that requires authentication
    return jsonify({
        'message': 'This is protected data',
        'user': auth.current_user()
    })

@app.route('/api/llm', methods=['POST'])
def llm_query():
    user_input = request.json.get('input')
    if user_input.startswith('@griffin') or user_input.startswith('%griffin'):
        # Extract the question part
        question = user_input.split(maxsplit=1)[1] if ' ' in user_input else ''
        # Make the API call to the LLM
        response = call_llm_api(question)
        return jsonify({'response': response})
    return jsonify({'error': 'Invalid input'}), 400

def call_llm_api(question):
    import requests
    import json

    url = 'https://api.your-llm-provider.com/v1/query'
    headers = {'Authorization': 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json'}
    payload = json.dumps({'model': 'Mistral-Nemo-12B-Instruct-2407', 'messages': [{'role': 'user', 'content': question}]})
    response = requests.post(url, headers=headers, data=payload)
    return response.json() if response.status_code == 200 else {'error': 'API call failed'}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### 3. Create HTML Templates

Create a templates directory:

```bash
mkdir -p ~/flask-app/templates
```

Create an index.html file:

```bash
nano ~/flask-app/templates/index.html
```

Add the following HTML:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Flask App</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #ddd;
        }
        .content {
            padding: 20px 0;
        }
        button {
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #45a049;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Flask App</h1>
            <div>
                Logged in as: <strong>{{ username }}</strong>
            </div>
        </div>
        <div class="content">
            <h2>Protected Content</h2>
            <p>This page is only visible to authenticated users.</p>
            <p>You can add your custom content here.</p>
        </div>
    </div>
</body>
</html>
```

### 4. Create a Systemd Service

Create a service file:

```bash
sudo nano /etc/systemd/system/flask-app.service
```

Add the following content:

```
[Unit]
Description=Flask Web Application
After=network.target

[Service]
User=admin
WorkingDirectory=/home/admin/flask-app
ExecStart=/home/admin/flask-app/venv/bin/gunicorn --bind 0.0.0.0:5000 app:app
Restart=always
StandardOutput=journal
StandardError=journal
SyslogIdentifier=flask-app
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 5. Enable and Start the Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable flask-app
sudo systemctl start flask-app
```

### 6. Check the Service Status

```bash
sudo systemctl status flask-app
```

### 7. Access the Web Application

Open a web browser and navigate to:
```
http://charlespi.local:5000
```

You'll be prompted for login credentials:
- Username: admin
- Password: griffin2020

## Customizing the Login System

### Change or Add Users

Edit the `app.py` file and modify the `users` dictionary:

```python
users = {
    "admin": generate_password_hash("griffin2020"),
    "user2": generate_password_hash("password2"),
    "user3": generate_password_hash("password3")
}
```

### Using Form-Based Login Instead of HTTP Basic Auth

If you prefer a form-based login instead of the browser's built-in authentication dialog, you can modify the application to use Flask's session management:

1. Update `app.py`:

```python
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Users dictionary
users = {
    "admin": generate_password_hash("griffin2020")
}

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and check_password_hash(users.get(username), password):
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return render_template('index.html', username=session['username'])
```

2. Create a login.html template:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Login</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
        }
        .login-form {
            display: flex;
            flex-direction: column;
            gap: 15px;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }
        .form-group {
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        input {
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            padding: 10px 15px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        .flash-message {
            color: red;
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <h1>Login</h1>
    
    {% if get_flashed_messages() %}
    <div class="flash-message">
        {{ get_flashed_messages()[0] }}
    </div>
    {% endif %}
    
    <form class="login-form" method="post">
        <div class="form-group">
            <label for="username">Username:</label>
            <input type="text" id="username" name="username" required>
        </div>
        <div class="form-group">
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" required>
        </div>
        <button type="submit">Login</button>
    </form>
</body>
</html>
```

## Cleaning Up Previous LLM Models

If you want to remove the previous LLM models and setup:

```bash
# Stop the service
sudo systemctl stop llm-server

# Disable the service
sudo systemctl disable llm-server

# Remove the service file
sudo rm /etc/systemd/system/llm-server.service

# Reload systemd
sudo systemctl daemon-reload

# Remove the model files
rm -rf ~/llm-server/models

# Optionally, remove the entire llm-server directory
rm -rf ~/llm-server
```

## Security Considerations

1. **Use HTTPS**: For production, consider setting up HTTPS using Nginx as a reverse proxy with Let's Encrypt certificates.

2. **Secure Passwords**: Use strong passwords and consider implementing password policies.

3. **Rate Limiting**: Implement rate limiting to prevent brute force attacks.

4. **Firewall**: Configure a firewall to restrict access to your Raspberry Pi.

5. **Regular Updates**: Keep your Raspberry Pi and all software up to date.


## API key for secure AI inference platform.

80f1d6aa-f48b-4028-bf90-19edfefead8d

```python
import requests
import json

url = "https://api.arliai.com/v1/chat/completions"

payload = json.dumps({
  "model": "Mistral-Nemo-12B-Instruct-2407",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Hello!"},
    {"role": "assistant", "content": "Hi!, how can I help you today?"},
    {"role": "user", "content": "Say hello!"}
  ],
  "repetition_penalty": 1.1,
  "temperature": 0.7,
  "top_p": 0.9,
  "top_k": 40,
  "max_tokens": 1024,
  "stream": False
})
headers = {
  'Content-Type': 'application/json',
  'Authorization': f"Bearer {ARLIAI_API_KEY}"
}

response = requests.request("POST", url, headers=headers, data=payload)
``` 