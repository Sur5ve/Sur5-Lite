#!/usr/bin/env python3
"""
Beta Version Splash Screen
Professional splash screen displayed during application initialization
Following modern UI/UX best practices (2024)
"""

from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QProgressBar
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont


class SplashScreen(QWidget):
    """Modern splash screen for Beta Version application startup
    
    Design Philosophy:
    - Product-over-company branding (Beta Version prominent, Redacted subtle)
    - Minimalist & clean design
    - Modern glassmorphism-inspired aesthetic
    - 2-3 second optimal display duration
    - High contrast typography for readability
    """
    
    # Signal emitted when splash screen is ready to close
    ready_to_close = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configure window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        
        # Beta Version color palette (matching main app theme)
        self.bg_color = "#1E2329"  # Dark background
        self.primary_color = "#20B2AA"  # Teal/cyan accent (AI/tech feel)
        self.text_color = "#E8E8E8"  # High contrast text
        self.muted_color = "#94A3B8"  # Subtle secondary text
        self.progress_bg = "#2A3441"  # Progress bar background
        self.progress_fill = "#20B2AA"  # Teal progress fill
        
        # Set fixed size (slightly larger for better proportions)
        self.setFixedSize(480, 300)
        
        # Setup UI
        self._setup_ui()
        
        # Center on screen
        self._center_on_screen()
        
    def _setup_ui(self):
        """Setup the splash screen UI with modern design principles"""
        # Set background with subtle border for depth
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {self.bg_color};
                border-radius: 16px;
                border: 1px solid #2A3441;
            }}
        """)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 40, 40, 40)
        main_layout.setSpacing(0)
        
        # Spacer
        main_layout.addStretch(2)
        
        # Product name (PRIMARY - large and bold)
        self.title_label = QLabel("Beta Version")
        title_font = QFont("Segoe UI", 48, QFont.Weight.Bold)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet(f"""
            QLabel {{
                color: {self.primary_color};
                background: transparent;
                padding: 0;
                margin: 0;
                letter-spacing: 2px;
            }}
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.title_label)
        
        # Company attribution (SECONDARY - subtle)
        main_layout.addSpacing(4)
        self.company_label = QLabel("by Redacted")
        company_font = QFont("Segoe UI", 11, QFont.Weight.Normal)
        self.company_label.setFont(company_font)
        self.company_label.setStyleSheet(f"""
            QLabel {{
                color: {self.muted_color};
                background: transparent;
                padding: 0;
                margin: 0;
                letter-spacing: 1px;
            }}
        """)
        self.company_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.company_label)
        
        # Tagline
        main_layout.addSpacing(16)
        self.subtitle_label = QLabel("Advanced AI Desktop Assistant")
        subtitle_font = QFont("Segoe UI", 13, QFont.Weight.Normal)
        self.subtitle_label.setFont(subtitle_font)
        self.subtitle_label.setStyleSheet(f"""
            QLabel {{
                color: {self.text_color};
                background: transparent;
                padding: 0;
                margin: 0;
            }}
        """)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.subtitle_label)
        
        # Spacer
        main_layout.addSpacing(36)
        
        # Progress bar (modern smooth design)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)  # Slightly thicker for visibility
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {self.progress_bg};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {self.primary_color},
                    stop:1 #1D9A92
                );
                border-radius: 3px;
            }}
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Status label
        main_layout.addSpacing(14)
        self.status_label = QLabel("Initializing Beta Version...")
        status_font = QFont("Segoe UI", 11, QFont.Weight.Normal)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {self.text_color};
                background: transparent;
                padding: 0;
                margin: 0;
            }}
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.status_label)
        
        # Spacer
        main_layout.addStretch(2)
        
        # Version label
        self.version_label = QLabel("Version 2.0.0")
        version_font = QFont("Segoe UI", 9, QFont.Weight.Normal)
        self.version_label.setFont(version_font)
        self.version_label.setStyleSheet(f"""
            QLabel {{
                color: {self.muted_color};
                background: transparent;
                padding: 0;
                margin: 0;
            }}
        """)
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.version_label)
        
    def _center_on_screen(self):
        """Center the splash screen on the primary screen"""
        try:
            from PySide6.QtGui import QGuiApplication
            screen = QGuiApplication.primaryScreen()
            if screen:
                screen_geometry = screen.availableGeometry()
                x = (screen_geometry.width() - self.width()) // 2
                y = (screen_geometry.height() - self.height()) // 2
                self.move(x, y)
        except Exception:
            pass
            
    def update_progress(self, value: int, status: str = ""):
        """Update progress bar and status text
        
        Args:
            value: Progress value (0-100)
            status: Status message to display
        """
        self.progress_bar.setValue(value)
        if status:
            self.status_label.setText(status)
        
        # Force UI update
        self.repaint()
        
    def set_status(self, status: str):
        """Set status message without changing progress
        
        Args:
            status: Status message to display
        """
        self.status_label.setText(status)
        self.repaint()
        
    def finish(self):
        """Close the splash screen gracefully"""
        self.ready_to_close.emit()
        QTimer.singleShot(200, self.close)



