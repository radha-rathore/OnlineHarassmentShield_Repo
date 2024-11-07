from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import geminiClassifier

app = Flask(__name__)

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'jfif', 'mp3', 'wav', 'mp4', 'mov', 'ogg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = 'your_secret_key'

# In-memory storage for simplicity
users = {
    "perpetrator": {"username": "perpetrator", "messages": []},
    "recipient": {"username": "recipient", "messages": []}
}
reports = []

# Categorization function for messages
def categorize_message(content=None, filetype=None, filePath= None):
    
    if content:
        category, identifier = geminiClassifier.receiveMessageforGemini(content, content_Type= 'text')
        if identifier== "malicious":
            return True, category

    if filetype in ['image', 'audio', 'video']:
        category, identifier = geminiClassifier.receiveMessageforGemini(content, content_Type= filetype, file_path = filePath)
        if identifier== "malicious":
            return True, category

    return False, None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/send_message', methods=['GET', 'POST'])
def send_message():
    if request.method == 'POST':
        content = request.form.get('content')
        file = request.files.get('file')
        file_url = None
        filetype = None

        # Check if only text or only file is provided
        if content and not file:
            is_malicious, category = categorize_message(content=content)
        elif file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            # file_url = f"{app.config['UPLOAD_FOLDER']}/{filename}"
            file_url = f"uploads/{filename}"
            file_extension = filename.rsplit('.', 1)[1].lower()
            filetype = 'image' if file_extension in ['png', 'jpg', 'jpeg', 'jfif'] else \
                       'audio' if file_extension in ['mp3', 'wav', 'ogg'] else 'video'
            is_malicious, category = categorize_message(filetype=filetype, filePath= f"{app.config['UPLOAD_FOLDER']}/{filename}")
        else:
            flash("Please provide either text or a single file (image, audio, or video).")
            return redirect(url_for('send_message'))

        users["recipient"]["messages"].append({
            "sender": "perpetrator",
            "content": content,
            "file_url": file_url,
            "filetype": filetype,
            "timestamp": datetime.now(),
            "is_malicious": is_malicious,
            "category": category
        })
        
        return redirect(url_for('view_messages'))
    return render_template('send_message.html')

@app.route('/view_messages')
def view_messages():
    recipient_messages = users["recipient"]["messages"]
    print(recipient_messages)
    return render_template('view_messages.html', messages=recipient_messages)

@app.route('/report_message/<int:message_index>', methods=['GET', 'POST'])
def report_message(message_index):
    if request.method == 'POST':
        reason = request.form.get('reason')
        message = users["recipient"]["messages"][message_index]
        reports.append({"message": message, "reason": reason, "reported_at": datetime.now()})
        return redirect(url_for('view_messages'))
    return render_template('report_message.html', message_index=message_index)

if __name__ == '__main__':
    app.run(debug=True)
