# nullog

An automated logbook system that securely manages and submits logbook entries.

## 🚀 Features

- **Secure Session Management**: Encrypted storage of login credentials and session data
- **Comprehensive Logging**: Detailed logging system for debugging and monitoring
- **Robust Error Handling**: User-friendly error messages and graceful error recovery
- **CSV Import**: Bulk import of logbook entries from CSV files
- **Automatic Validation**: Comprehensive validation of dates, times, and data formats
- **Session Recovery**: Automatic re-authentication when sessions expire
- **Progress Tracking**: Real-time progress indicators for bulk operations

## 🔒 Security Improvements

### Secure Storage
- **Encryption**: All sensitive data (cookies, user agents) are encrypted using Fernet (AES-128)
- **Key Derivation**: PBKDF2 with 100,000 iterations for secure key generation
- **Salt**: Unique salt for each encryption key
- **Password Protection**: Optional password protection for encryption keys

### Session Management
- **Secure Cookies**: Encrypted storage of session cookies
- **Automatic Cleanup**: Secure deletion of sensitive data
- **Session Validation**: Proper validation of session data integrity

## 📝 Logging System

### Log Levels
- **DEBUG**: Detailed debugging information
- **INFO**: General information about program execution
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failed operations

### Log Features
- **Daily Rotation**: New log file for each day
- **Structured Format**: Timestamp, level, function, line number, and message
- **File and Console**: Logs to both file and console (warnings/errors only)
- **UTF-8 Encoding**: Proper handling of international characters

### Log Location
- Logs are stored in the `logs/` directory
- Format: `nullog_YYYYMMDD.log`

## 🛡️ Error Handling

### Input Validation
- **Date Validation**: Comprehensive date format and range checking
- **Time Validation**: 24-hour format validation with business logic
- **CSV Validation**: Robust CSV parsing with detailed error reporting
- **Type Checking**: Proper type validation for all inputs

### User Experience
- **Clear Error Messages**: User-friendly error descriptions
- **Graceful Degradation**: Program continues running when possible
- **Retry Logic**: Automatic retry for transient failures
- **Keyboard Interrupt**: Proper handling of Ctrl+C interruptions

### Network Resilience
- **Timeout Handling**: Configurable timeouts for all network requests
- **Connection Retry**: Automatic retry for connection failures
- **Session Recovery**: Automatic re-login on session expiration

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kangwijen/nullog.git
   cd nullog
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional):
   ```bash
   # Create .env file
   USER_EMAIL_NLG=your_email@example.com
   USER_PASSWORD_NLG=your_password
   SATURDAY_SUBMISSION=false
   ```

## 🚀 Usage

### Basic Usage
```bash
python main.py
```

### What you'll be prompted for
- Acceptance of the disclaimer
- Whether it is an odd semester (y/n)
  - If yes, the app selects the odd semester in the portal before proceeding
- Microsoft login (email/password) if no valid session is found
- CSV file path to import entries

### CSV Format
Create a CSV file with the following columns:
```csv
date,activity,clock_in,clock_out,description
2024-01-15,Development Work,09:00,17:00,Working on project features
2024-01-16,OFF,OFF,OFF,OFF
```

### CSV Requirements
- **Date Format**: YYYY-MM-DD
- **Time Format**: HH:MM (24-hour) or OFF
- **Activity**: Any text or OFF
- **Description**: Any text or OFF
- **OFF Consistency**: When any field is OFF, all fields must be OFF
- **Available Months**: The app validates that all months in your CSV exist in the portal’s month list. If any are missing (e.g., different semester/term), it lists them and aborts.

## 📁 Project Structure

```
nullog/
├── main.py             # Main application entry point
├── utils/              # Application modules
│   ├── api.py          # API interaction functions
│   ├── login.py        # Authentication and login handling
│   ├── csv_parser.py   # CSV parsing and validation
│   ├── utils.py        # Utility functions and secure storage
│   ├── cookies.py      # Cookie management
│   ├── config.py       # Configuration management
│   ├── constants.py    # Application constants
│   └── display.py      # User interface and display functions
├── requirements.txt    # Python dependencies
├── README.md           # This file
├── VERSION             # Current release version
└── sample_logbook.csv  # Example CSV
```

## 🔧 Configuration

### Environment Variables
- `USER_EMAIL_NLG`: Your email address
- `USER_PASSWORD_NLG`: Your password
- `SATURDAY_SUBMISSION`: Set to "true" to allow Saturday submissions

### Sessions and Cookies
- The app securely stores session cookies and user agent (encrypted) and reuses them for API calls.
- If cookies are missing or stale, it automatically logs in again and refreshes the session.
- You’ll still be asked to choose odd semester at the start so the correct term is selected during login.

## ⚠️ Disclaimer

This tool is provided as-is with no warranty. Users are responsible for:
- Verifying all data before submission
- Understanding that existing entries may be overwritten
- Ensuring compliance with institutional policies
- Taking full responsibility for all submitted entries
---

**Note**: This tool is designed for educational purposes and should be used responsibly in accordance with your institution's policies.