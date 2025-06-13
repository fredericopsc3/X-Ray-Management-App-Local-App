# X-ray Management Application

## 🦷 About
A desktop application for managing dental X-ray images with automated detection capabilities for various dental conditions using YOLO object detection.

## Important
This project is part of the final year project for the Computer Engineering degree at UFP, academic year 2024/2025.
Links to other parts of the project:
AI model training: [https://github.com/fredericopsc3/X-Ray-Management-App-AI-Training]
Web application: [https://github.com/fredericopsc3/X-Ray-Management-App-Web-App]

This project serves solely as an example of a Laravel-based web application for dental X-ray management with artificial intelligence. It is important to note that the AI used in this project is for demonstration purposes only and should not be used in production without evaluation by qualified specialists.

## Features
- User Authentication : Secure login and registration system
- Patient Management : Add, view, and search patient records
- X-ray Analysis :
  - Upload and store dental X-ray images
  - Automated detection of dental conditions:
    - Impacted teeth
    - Caries (tooth decay)
    - Peri Lesions
    - Deep Caries
- Interactive Viewing : Zoomable X-ray viewer with pan capabilities
- Database Storage : Local SQLite database for patient and X-ray records
## Technologies Used
- Frontend : PySide6 (Qt for Python)
- Machine Learning : Ultralytics YOLO for object detection
- Database : SQLite3
- Additional Tools : sqlite-utils
## Installation
1. Clone the repository
2. Install the required dependencies:
```
pip install -r requirements.txt
```

## Usage
1. Run the application:
```
python app.py
```
2. Register a new account or login with existing credentials
3. Add patients and their X-ray images
4. Use the immediate test feature for quick X-ray analysis
5. View and manage patient records
## Features in Detail
### Patient Management
- Add new patients with name, date of birth, and email
- Search patients by name
- View patient history and associated X-rays
### X-ray Analysis
- Upload X-ray images for patients
- Automatic detection of dental conditions
- Visual display of detection results with bounding boxes
- Zoomable interface for detailed examination
### User Interface
- Clean and intuitive design
- Easy navigation between patients and X-rays
- Interactive viewing controls (zoom, pan)
## Requirements
- Python 3.x
- PySide6
- Ultralytics
- sqlite-utils
## License
This project is proprietary software. All rights reserved.

