#!/usr/bin/env python3
"""
Responsive Sidebar - Adapts layout to avoid vertical scrolling

Sur5 Lite — Open Source Edge AI
Copyright (c) 2024-2026 Sur5ve LLC
Licensed under MIT License
https://sur5ve.com
"""

from PySide6.QtCore import QObject, Qt, QEvent, QTimer
from PySide6.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QGridLayout, QSizePolicy


class ResponsiveSidebar(QObject):
    """Adapts group margins/spacing to avoid vertical scrolling in the sidebar.

    Keep control heights accessible (32–34 px). Only margins/spacing
    are compacted as space shrinks.
    """

    def __init__(
        self,
        sidebar_widget: QWidget,
        model_group: QGroupBox,
        config_group: QGroupBox,
        info_group: QGroupBox,
    ) -> None:
        super().__init__(sidebar_widget)
        self.root = sidebar_widget
        self.model_group = model_group
        self.config_group = config_group
        self.info_group = info_group

        # Prevent infinite loop jittering
        self._is_refitting = False
        self._pending_refit = False

        # Watch ONLY the root for resize events
        self.root.installEventFilter(self)

        # Info group is compact and does not grow tall
        self.info_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

    def eventFilter(self, obj, ev):
        # ONLY react to window resize, nothing else to prevent feedback loop
        if ev.type() == QEvent.Resize and obj == self.root:
            if not self._is_refitting:
                self._schedule_refit()
        return super().eventFilter(obj, ev)
    
    def _schedule_refit(self):
        """Schedule a layout refit, preventing multiple concurrent refits"""
        if self._is_refitting:
            self._pending_refit = True
            return
        QTimer.singleShot(50, self._do_refit)
    
    def _do_refit(self):
        """Execute the layout refit with re-entrance protection"""
        if self._is_refitting:
            return
        
        self._is_refitting = True
        self._pending_refit = False
        
        try:
            self._layout_to_fit()
        finally:
            self._is_refitting = False
            # If another refit was requested during execution, schedule it
            if self._pending_refit:
                QTimer.singleShot(50, self._do_refit)

    def _layout_to_fit(self) -> None:
        available_height = max(0, self.root.height())

        # Comfortable tokens
        base_inset = 12
        base_spacing = 10
        min_inset = 10
        min_spacing = 8

        fixed_groups = [self.model_group, self.config_group, self.info_group]

        # Estimate total height of fixed groups using size hints
        fixed_height = 0
        for gb in fixed_groups:
            fixed_height += gb.sizeHint().height()

        # Approximate chrome: borders + title chip etc.
        frame_overhead = 50
        outer_gutters = 20
        num_gaps = len(fixed_groups)
        inter_group_gaps = base_spacing * num_gaps

        budget = available_height - (fixed_height + frame_overhead + outer_gutters + inter_group_gaps)

        # Densify ONLY when space is extremely tight
        if budget < 100:
            scale = max(0.90, budget / 120.0) if budget > 0 else 0.90
        else:
            scale = 1.0

        inset = int(min_inset + (base_inset - min_inset) * scale)
        spacing = int(min_spacing + (base_spacing - min_spacing) * scale)

        # Apply margins/spacing uniformly
        for gb in fixed_groups:
            lay = gb.layout()
            if isinstance(lay, (QVBoxLayout, QGridLayout)):
                lay.setContentsMargins(inset, inset, inset, inset)
                lay.setSpacing(spacing)

        # Ensure UNIFORM gaps between titled groups across panels and root sidebar
        root_layout = self.root.layout()
        if isinstance(root_layout, QVBoxLayout):
            root_layout.setSpacing(spacing)

        model_panel_parent = self.model_group.parentWidget()
        if model_panel_parent is not None:
            model_panel_layout = model_panel_parent.layout()
            if isinstance(model_panel_layout, QVBoxLayout):
                model_panel_layout.setSpacing(spacing)
