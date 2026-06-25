[README.md](https://github.com/user-attachments/files/29342696/README.md)
# TubercuLens - An Imaged-Based AI Integrated Microscopic Detection System for Identifying Mycobacterium tuberculosis in Sputum Smears

`v5.5` · Python 3.11+ · RoboFlow · YOLOv8 · MediaPipe · Flask

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)](https://python.org)
[![RoboFlow](https://img.shields.io/badge/AI-RoboFlow-1a73e8?style=flat-square)](https://roboflow.com/)
[![Flask](https://img.shields.io/badge/Web-Flask-000?style=flat-square&logo=flask)](https://flask.palletsprojects.com/)
[![YOLOv8](https://img.shields.io/badge/AI-YOLOv8-00c853?style=flat-square)](https://ultralytics.com/)
[![MediaPipe](https://img.shields.io/badge/AI-MediaPipe-FF6F00?style=flat-square)](https://mediapipe.dev/)
[![License](https://img.shields.io/badge/License-Proprietary-red?style=flat-square)]()

A Flask-based web application that uses AI/ML technology to detect tuberculosis (TB) in chest X-ray images. TubercuLens provides automated batch processing, patient record management, and comprehensive reporting for TB detection and analysis.

### Authors

**Lead Developer**: PLEMA Research Team - Ali R. Goyena, Angela Marie B. Oasay, Edreah Eve I. Estimo

**Focus**: AI-enabled Medical Image Analysis & TB Detection System

## 📋 Key Features

| Feature | Description |
|---------|-------------|
| 🎥 **AI-Powered Detection** | Automated analysis of medical X-ray images using advanced ML models |
| 📦 **Batch Processing** | Process multiple images simultaneously for efficient workflow |
| 🔐 **Secure Authentication** | User login and account management with secure credentials |
| 👥 **Patient Records** | Store and retrieve comprehensive patient information and history |
| 📄 **Automated Reports** | Generate detailed PDF analysis reports with visual overlays |
| 📊 **Analytics Dashboard** | Real-time statistics and trends with visual charts |
| 🔄 **Image Analysis** | Side-by-side image comparison and result overlays |
| 💾 **Data Management** | Local persistent storage with security controls |
| 🎨 **Responsive UI** | Modern web-based interface with interactive elements |

## 🏗️ Architecture

```
PLEMA_Gold1/
├── app.py                      # Main Flask application (core logic)
├── reset_account.py            # Utility to reset user credentials
├── plema.db                    # SQLite database (auto-created)
│
├── static/                     # Static assets and file storage
│   ├── style.css              # Main application stylesheet
│   ├── uploads/               # Uploaded X-ray images
│   ├── outputs/               # Analyzed/processed image results
│   ├── reports/               # Generated PDF reports
│   └── New folder/            # Additional UI assets
│
├── templates/                  # Flask HTML templates
│   ├── index.html             # Main dashboard and workspace
│   ├── login.html             # User authentication page
│   ├── signup.html            # Account registration page
│   └── reset.html             # Credential reset page
│
├── data/                       # Runtime data (auto-generated)
│   ├── settings.json          # Application configuration
│   ├── alerts_log.json        # Detection history
│   └── profiles.json          # Patient profiles
│
└── README.md                   # Project documentation
```

## 🧭 Application Navigation

The dashboard is organized into key workspaces:

| Workspace | Purpose |
|-----------|---------|
| **Dashboard** | Main interface with upload, processing, and quick stats |
| **Records** | View and manage patient detection history |
| **Analytics** | Charts and statistical trends over time |
| **Reports** | Generate, view, and export analysis reports |
| **Settings** | Configure detection parameters and preferences |
| **Account** | User profile and authentication management |

## 🚀 Getting Started

### Prerequisites

- **Python 3.7** or higher
- **pip** (Python package manager)
- **Modern web browser** (Chrome, Firefox, Safari, or Edge)
- **~2GB free disk space** for database and image storage

### Installation

1. Download and navigate to the project directory
2. Install required dependencies
3. Initialize the application
4. Access through your web browser at `http://localhost:5000`

Refer to `app.py` for detailed setup instructions.

## 🔑 Authentication

- **Secure Login System**: User credentials stored securely
- **Account Creation**: Authorized account setup with verification
- **Session Management**: Automatic session handling with timeout protection
- **Password Reset**: Use `reset_account.py` to reset credentials if needed

## 📊 How to Use

1. **Login**: Access your account with secure credentials
2. **Upload**: Submit medical images for analysis (JPG, JPEG, PNG)
3. **Process**: Run analysis on uploaded images
4. **Review**: View detection results and comparisons
5. **Report**: Generate and export analysis reports
6. **Track**: Monitor results and statistics over time

## ⚙️ Configuration

Application settings are configured in `app.py`. Key parameters include detection thresholds and report formatting options. For details, refer to the configuration section in the main application file.

## 🗄️ Data Storage

The application uses a local SQLite database to store:
- Patient analysis records and results
- User account information
- Application settings and preferences
- Detection history and metadata

## 🔐 Security & Privacy

### Data Protection
- **Secure Authentication**: Login credentials protected with secure storage
- **Session Security**: Automatic session timeout for unauthorized access prevention
- **Input Validation**: File upload validation to prevent malicious files
- **Access Control**: User-specific data isolation and access restrictions

### Privacy Practices
- **Local Storage**: All data stored locally on your system by default
- **No External Sharing**: Patient data remains within your organization
- **Minimal Data Collection**: Only essential information required for analysis
- **Data Retention**: You control when data is stored, modified, or deleted
- **Compliance Ready**: Designed to support privacy regulations (GDPR, HIPAA, etc.)

### User Responsibilities
- Regularly back up your database (`plema.db`)
- Use HTTPS in production environments
- Restrict access to the application to authorized users only
- Maintain strong credentials and change passwords regularly
- Monitor for unauthorized access attempts

## 📝 Supported Image Formats

- JPG / JPEG
- PNG

## 🛠️ Troubleshooting

For common issues:
- Verify all dependencies are properly installed
- Ensure the application port is available
- Check file permissions for upload and output directories
- Review application logs for detailed error information
- Use `reset_account.py` if you need to reset user credentials

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| Flask | ≥2.0.0 | Web application framework |
| werkzeug | ≥2.0.0 | Secure filename handling and utilities |
| Pillow | ≥9.0.0 | Image processing and manipulation |
| opencv-python | ≥4.5.0 | Computer vision and image analysis |
| requests | ≥2.25.0 | HTTP requests for API communication |
| sqlite3 | Built-in | Local database management |
| python-docx | ≥0.8.11 | Report generation (DOCX format) |
| numpy | ≥1.20.0 | Numerical array operations |

## 🔄 Batch Processing

- Process multiple images simultaneously for efficiency
- Configurable analysis parameters
- Progress tracking during analysis

## 💻 Platform Compatibility

| Platform | Status | Notes |
|----------|--------|-------|
| **Windows 10/11** | ✅ Supported | Full feature support |
| **Linux (Ubuntu/Mint)** | ✅ Supported | Primary development target |
| **macOS** | ✅ Supported | Flask and dependencies available |
| **Raspberry Pi** | 🟡 Partial | Limited by processing power, suitable for storage only |

## 📈 Analytics

- View detection statistics and trends
- Historical record tracking
- Case distribution analysis

## 🚀 Production Deployment

For production environments:
- Enable HTTPS/SSL encryption
- Use a dedicated production server
- Implement additional access controls
- Set up regular backups
- Configure firewalls and network security
- Monitor system logs for security events

## � License

This project is provided for research and educational purposes.

---

## 📚 Additional Resources

- **Code**: Review implementation in `app.py` and supporting modules
- **Database**: SQLite schema defined in `init_db()` function
- **Frontend**: HTML templates in `templates/` directory
- **Styling**: CSS customization in `static/style.css`
- **Issues**: Check troubleshooting section or application logs

---

**Version**: TubercuLens v5.5 (Batch Processing Complete)  
**Status**: Active Development  
**Built for**: Medical Research & Clinical Education
