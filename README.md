# PhantomTap - Stealth Keystroke Analytics

![PhantomTap Banner](https://via.placeholder.com/1200x300/0a1929/00FF88?text=PhantomTap+👻)

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-00bcd4)](https://github.com/TomSchimansky/CustomTkinter)
[![Status](https://img.shields.io/badge/status-active-brightgreen)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)]()

> **⚠️ EDUCATIONAL PURPOSE ONLY**  
> This tool is designed for educational purposes, security research, and testing on your own devices. Unauthorized use of keyloggers is illegal and unethical. Always obtain proper consent before monitoring any system.

## 📋 Overview

**PhantomTap** is a sophisticated, professional-grade keystroke analytics application with a modern, cyberpunk-inspired GUI. It provides real-time monitoring, comprehensive statistics, and multiple export formats for captured keystroke data. Built with Python and CustomTkinter, it features a sleek dark theme with Phantom Green accents.

![Dashboard Preview](https://via.placeholder.com/800x450/132f4c/00FF88?text=PhantomTap+Dashboard+Preview)

## ✨ Features

### 🔐 Authentication System
- Secure user registration and login
- Password hashing with SHA-256
- SQLite database for user management
- Password visibility toggle

### ⌨️ Advanced Keylogging
- Real-time keystroke capture
- Special key handling (Enter, Space, Backspace, Tab, etc.)
- Session-based logging with custom names
- Automatic word counting and text reconstruction
- Backspace-aware typing accuracy calculation

### 📊 Comprehensive Analytics
- **Live Statistics Dashboard**
  - Total keystrokes counter
  - Words typed counter
  - Typing speed (KPM - Keys Per Minute)
  - Words per minute (WPM)
  - Session duration timer
  - Real-time accuracy percentage

- **Performance Metrics**
  - Typing speed analysis
  - Key frequency distribution
  - Top 10 most used keys
  - Hourly activity tracking
  - Session quality assessment

### 🎨 Modern UI/UX
- Cyberpunk-inspired dark theme
- Phantom Green (#00FF88) accent color
- Responsive 1600x900 layout
- Real-time text reconstruction preview
- Animated status indicators
- Professional card-based design
- Gradient backgrounds and hover effects

### 💾 Export Capabilities
Multiple export formats with rich formatting:

1. **📄 Text Document (.txt)**
   - Human-readable formatted reports
   - ASCII art borders and sections
   - Complete session information
   - Reconstructed text with line numbers
   - Key frequency bar charts
   - Performance summary with emojis

2. **📊 JSON Data (.json)**
   - Structured data format
   - ISO-formatted timestamps
   - Complete session metadata
   - Key frequency analysis
   - Reconstructed text preservation

3. **📈 CSV Spreadsheet (.csv)**
   - Data analysis ready
   - Detailed keystroke logs
   - Key type categorization
   - Statistical summaries
   - Compatible with Excel/Google Sheets

### 🎯 Real-time Features
- Live text reconstruction preview
- Dynamic statistics updates (500ms refresh)
- Session status indicators
- Active/inactive state management
- Professional notification dialogs

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/phantomtap.git
cd phantomtap
```

### Step 2: Install Dependencies
```bash
pip install customtkinter pynput
```

### Step 3: Run the Application
```bash
python phantomtap.py
```

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| customtkinter | Latest | Modern GUI framework |
| pynput | Latest | Keyboard event monitoring |
| sqlite3 | Built-in | User database management |
| hashlib | Built-in | Password hashing |
| json | Built-in | JSON export functionality |
| csv | Built-in | CSV export functionality |
| threading | Built-in | Background processing |
| datetime | Built-in | Timestamp management |

## 🎮 How to Use

### 1. **Authentication**
- Register a new account with username and password
- Login with existing credentials
- Password visibility toggle for convenience

### 2. **Start a Session**
1. Enter a session name (or use auto-generated)
2. Click "ACTIVATE" to start monitoring
3. Begin typing - everything is captured in real-time

### 3. **Monitor Activity**
- Watch live statistics update
- See reconstructed text in preview pane
- Track typing speed and accuracy
- Monitor session duration

### 4. **Export Data**
1. Click "EXPORT" button
2. Choose export format (TXT/JSON/CSV)
3. Select save location
4. View comprehensive reports

### 5. **Manage Sessions**
- **DEACTIVATE**: Stop current monitoring session
- **CLEAR**: Clear all logs and reset counters
- **LOGOUT**: Return to login screen

## 📊 Data Structure

### Session Information
```json
{
  "session_info": {
    "name": "Session_1430",
    "id": "Session_1430_20240101_143022",
    "start_time": "2024-01-01T14:30:22",
    "total_keys": 1250,
    "words_typed": 187,
    "duration": "00:15:30",
    "typing_accuracy": 94.5
  }
}
```

### Keystroke Logging
```json
{
  "keystrokes": [
    {
      "timestamp": "2024-01-01T14:30:23.456",
      "time_display": "14:30:23",
      "key": "H",
      "key_display": "H"
    }
  ]
}
```

## 🎨 UI Components

### Sidebar
- **Logo & Branding**: PhantomTap identity with ghost emoji
- **Session Configuration**: Custom session naming
- **System Status**: Active/Standby indicator with counter
- **Control Panel**: All action buttons (Activate, Deactivate, Clear, Export, Logout)
- **User Info**: Logged-in user display

### Main Content
- **Statistics Cards**: 5 real-time metric displays
- **Text Preview**: Live reconstruction panel
- **Info Bar**: Current session details

## 🔒 Security Features

- **Password Security**: SHA-256 hashing for all passwords
- **Session Isolation**: Each session has unique ID
- **Data Privacy**: All data stored locally
- **User Authentication**: SQLite database with integrity checks

## 📁 Project Structure

```
phantomtap/
│
├── phantomtap.py          # Main application file
├── phantomtap.db          # SQLite user database
│
├── exports/               # Exported data directory
│   ├── session_*.txt     # Text exports
│   ├── session_*.json    # JSON exports
│   └── session_*.csv     # CSV exports
│
└── README.md              # This file
```

## ⚠️ Important Notes

### Legal & Ethical Considerations
- **Educational Purpose Only**: This tool is for learning about cybersecurity
- **Own Devices Only**: Only use on systems you own
- **Consent Required**: Always obtain explicit permission before monitoring
- **Check Local Laws**: Keylogging may be regulated in your jurisdiction

### System Requirements
- **OS**: Windows 10/11, macOS, Linux (with X11)
- **RAM**: 500MB minimum
- **Disk**: 100MB for application
- **Python**: 3.8 or higher

### Limitations
- Requires pynput library for keyboard hooks
- May require administrator/root privileges on some systems
- Not designed for malicious use

## 🔧 Troubleshooting

### Common Issues

1. **"pynput not installed" error**
   ```bash
   pip install pynput
   ```

2. **Application doesn't start**
   - Verify Python version: `python --version`
   - Check all dependencies installed

3. **No keystrokes captured**
   - Run as administrator/root
   - Check antivirus/firewall settings
   - Verify pynput installation

4. **Export fails**
   - Check write permissions in save directory
   - Ensure disk has free space
   - Try different export format

## 🚧 Future Enhancements

- [ ] Cloud backup integration
- [ ] Advanced data visualization charts
- [ ] Multi-language support
- [ ] Plugin system for extensions
- [ ] Encrypted export options
- [ ] Network monitoring capabilities
- [ ] Custom hotkey configuration
- [ ] Session comparison analytics
- [ ] Export to PDF with formatting
- [ ] Real-time cloud sync

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for modern GUI components
- [pynput](https://github.com/moses-palmer/pynput) for keyboard monitoring
- Python community for excellent documentation
