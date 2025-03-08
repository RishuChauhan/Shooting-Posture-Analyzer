# Rifle Shooting Posture Analysis System

A comprehensive desktop application for real-time analysis and improvement of rifle shooting posture using computer vision and fuzzy logic.

## Overview

The Rifle Shooting Posture Analysis System is designed to help shooters improve their shooting stance through real-time posture analysis. Using computer vision, machine learning, and fuzzy logic, the application captures, analyzes, and provides feedback on a shooter's posture during practice sessions. It detects posture issues, tracks improvement over time, and generates detailed reports with actionable recommendations.

This system serves as a training assistant for competitive shooters and coaches, providing objective measurements and personalized feedback that would traditionally require expert human observation.

## Features

- **User Management**
  - Create and manage shooter profiles
  - Support for different user roles (shooter, coach)

- **Real-time Analysis**
  - Live video capture from webcam
  - Real-time posture analysis with instant feedback
  - Audio-triggered capture for analyzing posture at the moment of shooting
  - Overlay of joint angles and posture indicators

- **Session Recording and Playback**
  - Record shooting sessions with synchronized posture data
  - Frame-by-frame playback and analysis
  - Detailed joint angle measurements and comparisons to ideal positions

- **Performance Tracking**
  - Track progress over time with comprehensive metrics
  - Visualize improvement trends across multiple sessions
  - Identify persistent problem areas in shooting stance

- **3D Visualization**
  - 3D representation of shooter's posture
  - Adjustable camera angles to view pose from different perspectives
  - Comparison between actual and ideal postures

- **Reporting**
  - Generate detailed PDF reports with key metrics
  - Session-specific and progress reports
  - Actionable recommendations for improvement

## Technology Stack

- **Python 3**: Core programming language
- **PyQt6**: GUI framework
- **OpenCV**: Computer vision for video processing
- **MediaPipe**: Pose estimation and keypoint detection
- **SQLite**: Embedded database for data storage
- **Matplotlib**: Data visualization and plotting
- **NumPy**: Numerical processing
- **scikit-fuzzy**: Fuzzy logic for posture analysis
- **PyAudio**: Audio input and processing
- **ReportLab**: PDF report generation

## System Requirements

### Minimum Requirements
- **CPU**: Quad-core processor, 2.5 GHz or higher
- **RAM**: 8 GB or more
- **GPU**: Integrated graphics (dedicated GPU recommended)
- **Camera**: 720p webcam with 30fps capability
- **Microphone**: Basic integrated or external microphone
- **Storage**: 500 MB for application, plus storage for session recordings
- **OS**: Windows 10/11, macOS 10.15+, or Linux (Ubuntu 20.04+)

### Recommended Requirements
- **CPU**: Intel i5/i7 or AMD Ryzen 5/7
- **RAM**: 16 GB
- **GPU**: Dedicated graphics with CUDA support
- **Camera**: 1080p webcam with 60fps capability
- **Microphone**: External microphone with noise cancellation
- **Storage**: SSD with at least 10 GB free space

## Installation and Setup

### Prerequisites
Ensure you have Python 3.8 or newer installed on your system.

### Step 1: Clone the repository
```bash
git clone https://github.com/yourusername/shooting-posture-analyzer.git
cd shooting-posture-analyzer
```

### Step 2: Create a virtual environment
```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On macOS/Linux
source venv/bin/activate
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Initialize the database
```bash
python db_schema_updater.py
```

### Step 5: Run the application
```bash
python main.py
```

## Usage Guide

### First-time Setup
1. When you first launch the application, you'll be prompted to create a shooter profile
2. Navigate to the "Settings" screen to configure your camera and audio settings
3. Adjust analysis parameters if needed

### Recording a Session
1. Select your shooter profile from the "Profiles" screen
2. Navigate to the "Live Analysis" screen
3. Click "Start Recording" to begin your session
4. Practice your shooting while receiving real-time feedback
5. The system will automatically capture your posture when a shot is detected (if audio detection is enabled)
6. Click "Stop Recording" when finished
7. Save your session

### Reviewing a Session
1. Navigate to the "Replay & Analysis" screen
2. Select a session from the dropdown menu
3. Use the playback controls to review the session
4. View detailed joint angle analysis for each frame
5. Switch to the "3D Plot Analysis" screen for a 3D visualization of your posture

### Tracking Progress
1. Navigate to the "Performance Dashboard" screen
2. View your performance metrics and improvement trends
3. Check joint-specific analysis to identify areas needing improvement
4. Generate a progress report for detailed analysis

## Project Structure

The application is organized into several modules:

```
shooting-posture-analyzer/
├── core/                # Core functionality modules
│   ├── audio_detector.py      # Audio detection for shot capture
│   ├── data_manager.py        # Database operations
│   ├── pose_visualizer.py     # 3D pose visualization
│   ├── posture_analyzer.py    # Fuzzy logic posture analysis
│   ├── report_generator.py    # PDF report generation
│   └── video_processor.py     # Video capture and processing
├── ui/                  # User interface modules
│   ├── live_analysis.py       # Live analysis screen
│   ├── main_window.py         # Main application window
│   ├── performance.py         # Performance dashboard
│   ├── plot_3d.py             # 3D visualization screen
│   ├── profiles.py            # User profile management
│   ├── replay.py              # Session replay screen
│   └── settings.py            # Application settings
├── utils/               # Utility modules
│   ├── constants.py           # Application constants
│   ├── exceptions.py          # Custom exceptions
│   └── helpers.py             # Helper functions
├── database_util.py     # Database utility script
├── db_schema_updater.py # Database schema updater
├── main.py              # Application entry point
└── requirements.txt     # Dependencies
```

## Development

### Setting up the Development Environment
1. Follow the installation steps above
2. Install development dependencies:
```bash
pip install -r requirements-dev.txt
```

### Running Tests
```bash
pytest tests/
```

### Building the Application
To create a standalone executable:
```bash
pyinstaller main.spec
```

## Troubleshooting

### Common Issues

**Camera not detected**
- Ensure your camera is properly connected
- Check if other applications are using the camera
- Verify camera permissions in your OS settings

**Audio detection not working**
- Check if your microphone is properly connected
- Adjust the audio sensitivity in Settings
- Ensure you have appropriate permissions for microphone access

**Poor pose detection**
- Ensure good lighting conditions
- Wear contrasting clothing
- Position the camera at an appropriate distance and angle

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- MediaPipe team for the pose estimation framework
- OpenCV community for computer vision tools
- PyQt team for the GUI framework
- All contributors to the open-source libraries used in this project