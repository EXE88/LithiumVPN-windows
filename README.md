# LithiumVPN Windows Client

A modern, user-friendly VPN client built with PyQt6 for Windows, featuring a sleek interface and powerful connection management capabilities. Supplement of x-ui-accounter. Supports Xray.

## 🌟 Features

- **Modern UI Design**
  - Clean and intuitive interface built with PyQt6
  - Dark theme with professional color scheme
  - Smooth animations and transitions
  - System tray integration for background operation

- **Connection Management**
  - Multiple VPN configuration support
  - Real-time connection status monitoring
  - Bandwidth and days tracking for each config
  - Auto-reconnect capabilities

- **Security Features**
  - XRay client integration
  - Secure configuration storage
  - System proxy management
  - Connection state persistence

- **User Account System**
  - User authentication
  - Email verification
  - Profile management
  - Credit system with coin balance

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- PyQt6
- Windows OS

### Installation

1. Clone the repository:
```bash
git clone https://github.com/EXE88/LithiumVPN-windows.git
cd LithiumVPN-windows
```

2. Create and activate virtual environment:
```bash
python -m venv env
.\env\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the Application

```bash
python main.py
```

## 🏗️ Project Structure

```
├── assets/              # Application assets and icons
├── core/               # Core VPN functionality
│   ├── binding/       # Core bindings
│   ├── handlers/      # Connection handlers
│   └── temp/          # Temporary files
├── custom_widgets/     # Custom PyQt widgets
├── modules/           # Utility modules
├── ui/               # Qt Designer UI files
├── ui_python/        # Generated Python UI files
└── tests/            # Test suites
```

## 🔧 Configuration

The application uses several configuration files:

- `configuration.py` - Main application settings
- `core/temp/temp_init.json` - Temporary initialization data
- Various `.ui` files in the `ui/` directory for interface layouts

## 🎨 Custom Widgets

The application features several custom widgets for enhanced UI:

- `FancyLabel` - Enhanced label with animations
- `FancyRoundButton` - Customized round buttons
- `PopupToast` - Toast notifications
- `ClickableLabel` - Interactive labels
- `ConfigDelegateComboBox` - Specialized combobox for configs

## 🔐 Security

- Secure storage of VPN configurations
- Protected user credentials
- Safe proxy management
- Encrypted communication

## 📄 License

This project is licensed under the terms provided in `License.txt`.

## 🛠️ Built With

- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) - GUI Framework
- [XRay](https://github.com/XTLS/Xray-core) - Core VPN Technology
- [SQLite](https://www.sqlite.org/) - Local Database

## 🎯 Roadmap

- [ ] Multi-language support
- [ ] Advanced configuration editor
- [ ] Traffic statistics visualization
- [ ] Automatic updates
- [ ] Enhanced security features

## DO NOT FORGET

- for building project use :
```
pyinstaller --noconfirm --onedir --add-data "core/binding;core/binding" --add-data "core/temp;core/temp" --add-data "assets/icons;assets/icons" --add-data "assets/themes;assets/themes" --name LithiumVPN -i assets/icons/appicon.ico --uac-admin -w main.py && rm -r build/ LithiumVPN.spec
```
- for converting .ui file to .py use :
```
pyuic6 file.ui -o file.py
```
- for customizeing app to other templates (changeing icons,texts,domain,...) just edit configuration.py file
- for converting resources.qrc to resources_rc.py install and use pyrcc6 (but never forgot to remove this package and releated packages that uses pyside6 when building project also change every pyside6 importage to pyQt6 because if you dont do this staff you may get some errors during build proccess becuase of pyside6)
  
---

Made with ❤️ by EXE88
