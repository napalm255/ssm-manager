# SSM Manager (AWS)
A desktop application for managing SSM session on AWS cloud with a user-friendly GUI interface.

[![GitHub release (latest by date)](https://img.shields.io/github/v/release/napalm255/ssm-manager?style=flat-square)](https://github.com/napalm255/ssm-manager/releases)
[![GitHub](https://img.shields.io/github/license/napalm255/ssm-manager?style=flat-square)](https://github.com/napalm255/ssm-manager?tab=MIT-1-ov-file)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)
[![Bugs](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=bugs)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)
[![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)
[![Duplicated Lines (%)](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=duplicated_lines_density)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)
[![Lines of Code](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=ncloc)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)
[![Reliability Rating](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=reliability_rating)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)
[![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=napalm255_ssm-manager&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=napalm255_ssm-manager)

![Screenshot](images/screenshot.jpg)

  - [Description](#description)
  - [Features](#features)
    - [Core Functionality](#core-functionality)
    - [Instance Management](#instance-management)
    - [Connection Types](#connection-types)
    - [Active Connection Management](#active-connection-management)
    - [Additional Features](#additional-features)
  - [Requirements](#Requirements)
  - [Installation](#installation)
  - [Usage](#usage)
  - [Development](#development)
    - [Requirements](#requirements)
    - [Setup Development Environment](#setup-development-environment)
    - [Building from Source](#building-from-source)
  - [Contributing](#contributing)
  - [Bug reports](#bug-reports)
  - [Acknowledgments](#acknowledgments)
  - [Support](#support)


## Description

SSM Manager is a cross-platform desktop application that provides a web interface for managing AWS Systems Manager sessions.
It simplifies the process of connecting to EC2 instances through AWS Systems Manager by providing an intuitive interface for Shell sessions, RDP connections, custom port forwarding, and host port forwarding.

## Features

### Core Functionality
  - Runs as a system tray icon
  - Uses your default browser to display the UI
  - Easy switching between AWS profiles (including sso)
  - Region selection
  - Connection status monitoring
  - Maintain connections across multiple profiles

### Instance Management
- **Instance Listing**
  - Display of EC2 instances with SSM capability
  - Instance status updates
  - Instance details (Name, ID, Type, OS, State, IP Address ecc..)

### Connection Types
- **Shell Sessions**
  - Direct Shell connection to instances
  - Session monitoring and management

- **RDP Connections**
  - Automated RDP port forwarding setup
  - Dynamic local port allocation
  - Session monitoring and management
  - Integration with Windows Remote Desktop

- **Port Forwarding**
  - User-defined port forwarding
  - Dynamic local port allocation
  - Session monitoring and management
  - Remote host connection through instances
  

### Active Connection Management
- Real-time connection status monitoring
- Active session termination

### Additional Features
- Logging system with configurable levels
- Light and dark mode themes for the UI
- Customizable preferences (e.g., port range, log level, regions)

## Requirements

- Windows or Linux OS (Tested on Windows 11 and Fedora 40)
- AWS CLI installed and configured [[instructions here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)]
- AWS SSM Plugin for AWS CLI installed [[instructions here](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)]
- Valid AWS credentials configured (`aws configure [sso]`)

## Installation

A pre-built version is currently only available for Windows and comes in either a self extracting zip or a zip file.

1. Download the latest release from the releases page
2. Run the self extracting zip, `ssm_manager.exe`.
3. Ensure that AWS CLI and SSM Plugin are installed.
   ```powershell
   aws --version
   aws ssm start-session --version
   ```
5. Configure AWS CLI and log in to AWS. [**Instructions here**](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
6. Install the Session Manager plugin for AWS CLI. [**Instructions here**](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html)
7. Launch **SSM Manager**.

## Usage

1. Launch the application
2. Select your AWS profile and region
3. Click "Connect" to view available instances
4. Use the action buttons to establish connections:
   - Shell: Direct terminal access
   - RDP: Remote desktop connection
   - PORT: Custom port forwarding

## Development

### Requirements
- Python 3.12+
- flask
- boto3
- psutil
- pythonnet
- cachelib
- pystray
- colorama

### Setup Development Environment
```powershell
git clone https://github.com/napalm255/ssm-manager.git
cd ssm-manager
pipenv install -d
pipenv shell
inv run
```

### Building from Source

_This assumes you have already cloned the repository and are in the root directory of the project with an active virtual environment._

```powershell
inv build
```

### Packaging as a zipfile

```powershell
inv package
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## Bug reports

Create an issue on GitHub, please include the following (if one of them is not applicable to the issue then it's not needed):
- The steps to reproduce the bug
- Logs file ssm_manager.log
- The version of software
- Your OS & Browser including server OS
- What you were expecting to see

## Acknowledgments

- All contributors who helped improve this tool
- A bit support from AI
- Original development by [mauroo82](https://github.com/mauroo82)

## Support

If you encounter any problems or have suggestions, please open an issue in the GitHub repository.
