#!/usr/bin/env python3
"""
Response Progress Controller
Progressive microcopy controller for Tier 2 response loading
"""

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QLabel
from typing import Optional


class ResponseProgressController(QObject):
    """
    Progressive microcopy controller for Tier 2 response loading
    Updates text through 3 phases with conservative timing and animated dots
    """
    
    def __init__(self, progress_label: QLabel, parent=None):
        super().__init__(parent)
        self.progress_label = progress_label
        self._current_phase = 0
        self._dot_count = 1  # Start with 1 dot
        self._stopped = False
        
        # Phase definitions (without dots - added dynamically)
        self.phases = [
            "Sur is analyzing context",
            "Sur is drafting response",
            "Sur is refining wording"
        ]
        
        # Timer for dot animation (350ms like ProcessingHeader)
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._advance_dots)
        self._dot_timer.setInterval(350)  # 350ms per dot update
        
        # Timer for phase transitions (2 seconds = ~6 dot cycles)
        self._phase_timer = QTimer(self)
        self._phase_timer.timeout.connect(self._advance_phase)
        self._phase_timer.setInterval(2000)  # 2 seconds per phase
    
    def start(self):
        """Start progress updates with Phase 1"""
        self._stopped = False
        self._current_phase = 0
        self._dot_count = 1
        self._update_display()
        self._dot_timer.start()  # Start dot animation
        self._phase_timer.start()  # Start phase transitions
    
    def stop(self):
        """Stop all progress updates"""
        self._stopped = True
        self._dot_timer.stop()
        self._phase_timer.stop()
    
    def advance_to_phase_2(self):
        """
        Force advance to Phase 2 (called when thinking closes)
        This is the signal from Tier 1 completion
        """
        if self._stopped or self._current_phase >= 1:
            return
        self._current_phase = 1
        self._dot_count = 1  # Reset dots when advancing phase
        self._update_display()
    
    def _advance_dots(self):
        """Advance dot count (1 → 2 → 3 → 1)"""
        if self._stopped:
            return
        
        # Cycle dots: 1 → 2 → 3 → 1
        self._dot_count = (self._dot_count % 3) + 1
        self._update_display()
    
    def _advance_phase(self):
        """Advance to next phase (timer callback)"""
        if self._stopped:
            return
        
        # Cycle through phases: 0 → 1 → 2 → 0 → ...
        self._current_phase = (self._current_phase + 1) % len(self.phases)
        self._dot_count = 1  # Reset dots when changing phase
        self._update_display()
    
    def _update_display(self):
        """Update progress label with current phase text + animated dots"""
        if self._stopped or not self.progress_label:
            return
        
        if self._current_phase < len(self.phases):
            base_text = self.phases[self._current_phase]
            dots = "." * self._dot_count
            self.progress_label.setText(f"{base_text}{dots}")


