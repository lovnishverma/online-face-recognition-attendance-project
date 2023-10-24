import os
from flask import Flask, request, render_template, jsonify
import base64
import face_recognition
from werkzeug.utils import secure_filename
import csv
from datetime import datetime

UPLOAD_FOLDER = 'mysite/static/uploads'
KNOWN_FACES_FOLDER = 'mysite/static/known_faces'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['KNOWN_FACES_FOLDER'] = KNOWN_FACES_FOLDER
app.secret_key = "secret key"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def recognize_faces(image_path):
    # Load the known faces and encodings
    known_faces = []
    known_encodings = []

    # Load and encode the known faces
    known_faces_dir = app.config['KNOWN_FACES_FOLDER']
    for file_name in os.listdir(known_faces_dir):
        face_image = face_recognition.load_image_file(os.path.join(known_faces_dir, file_name))
        face_encoding = face_recognition.face_encodings(face_image)[0]

        known_faces.append(file_name.split('.')[0])
        known_encodings.append(face_encoding)

    # Load the image for face recognition
    img = face_recognition.load_image_file(image_path)
    recognized_faces = []

    # Process the input image
    face_locations = face_recognition.face_locations(img)
    face_encodings = face_recognition.face_encodings(img, face_locations)

    # Iterate over the face encodings in the input image
    for face_encoding in face_encodings:
        # Compare the face encoding with the known encodings
        matches = face_recognition.compare_faces(known_encodings, face_encoding)
        name = "Unknown"

        # Check if there is a match
        if True in matches:
            matched_indexes = [i for i, matched in enumerate(matches) if matched]
            name = known_faces[matched_indexes[0]]

        recognized_faces.append(name)

    return recognized_faces

def store_attendance(attendance):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    csv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{current_date}.csv")

    if not os.path.isfile(csv_file_path):
        with open(csv_file_path, 'w', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['Name', 'Date', 'Time'])

    with open(csv_file_path, 'r+', newline='') as csv_file:
        csv_reader = csv.reader(csv_file)
        lines = list(csv_reader)

        existing_names = [line[0] for line in lines[1:]]

        with open(csv_file_path, 'a', newline='') as f:
            csv_writer = csv.writer(f)

            for name in attendance:
                if name != "Unknown" and name not in existing_names:
                    current_time = now.strftime("%H:%M:%S")
                    csv_writer.writerow([name, current_date, current_time])

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/upload_known_faces', methods=['GET', 'POST'])
def upload_known_faces():
    if request.method == 'POST':
        files = request.files.getlist('file')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['KNOWN_FACES_FOLDER'], filename))
    return render_template('upload_known_faces.html')

@app.route('/recognize', methods=['POST'])
def recognize():
    if 'image' not in request.form:
        return jsonify({'error': 'No image data found.'}), 400

    # Decode the base64 image data
    image_data = request.form['image']
    image_data = image_data.replace('data:image/jpeg;base64,', '')
    image_data = image_data.encode()
    image_data = base64.b64decode(image_data)

    # Save the captured image locally
    filename = 'captured_image.jpg'
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    with open(file_path, 'wb') as f:
        f.write(image_data)

    # Perform face recognition
    recognized_faces = recognize_faces(file_path)

    # Store attendance
    store_attendance(recognized_faces)

    # Return the recognized faces
    return jsonify({'recognized_faces': recognized_faces})

@app.route('/attendance')
def view_attendance():
    current_date = datetime.date.today().strftime("%Y-%m-%d")
    return redirect(url_for('attendance', date=current_date))

@app.route('/attendance/<date>')
def show_attendance(date):
    # Construct the path to the CSV file
    csv_file_path = os.path.join(app.config['UPLOAD_FOLDER'], f'{date}.csv')

    # Read the attendance data from the CSV file
    attendance_data = []
    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        attendance_data = list(csv_reader)

    # Render the attendance.html template and pass the attendance data
    return render_template('attendance.html', date=date, attendance_data=attendance_data)

if __name__ == '__main__':
    app.run(debug=True)
