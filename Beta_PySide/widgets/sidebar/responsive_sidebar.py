#!/usr/bin/env python3
from PySide6.QtCore import QObject, Qt, QEvent, QTimer
from PySide6.QtWidgets import QWidget, QGroupBox, QVBoxLayout, QListWidget, QSizePolicy


class ResponsiveSidebar(QObject):
    """Adapts group margins/spacing and documents list height to avoid
    vertical scrolling in the sidebar at any window height.

    Keep control heights accessible (32–34 px). Only margins/spacing and
    low-priority text blocks are compacted as space shrinks.
    """

    def __init__(
        self,
        sidebar_widget: QWidget,
        model_group: QGroupBox,
        config_group: QGroupBox,
        info_group: QGroupBox,
        rag_group: QGroupBox,
        docs_group: QGroupBox,
        docs_list: QListWidget,
    ) -> None:
        super().__init__(sidebar_widget)
        self.root = sidebar_widget
        self.model_group = model_group
        self.config_group = config_group
        self.info_group = info_group
        self.rag_group = rag_group
        self.docs_group = docs_group
        self.docs_list = docs_list

        # Prevent infinite loop jittering
        self._is_refitting = False
        self._pending_refit = False

        # Watch ONLY the root for resize events
        self.root.installEventFilter(self)

        # Info group is compact and does not grow tall
        self.info_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.docs_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.docs_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # No horizontal scrollbar; let vertical appear inside the list if needed
        self.docs_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.docs_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

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
        min_inset = 8
        min_spacing = 6

        fixed_groups = [self.model_group, self.config_group, self.info_group, self.rag_group]

        # Estimate total height of fixed groups using size hints
        fixed_height = 0
        for gb in fixed_groups:
            fixed_height += gb.sizeHint().height()

        # Approximate chrome around documents section: borders + title chip etc.
        frame_overhead = 50
        outer_gutters = 20
        # Need spacing between all 5 groups (4 fixed + docs)
        num_gaps = len(fixed_groups) + 1
        inter_group_gaps = base_spacing * num_gaps

        budget = available_height - (fixed_height + frame_overhead + outer_gutters + inter_group_gaps)

        # Densify when space is tight
        if budget < 140:
            # Scale down more aggressively
            scale = max(0.75, budget / 160.0) if budget > 0 else 0.75
        else:
            scale = 1.0

        inset = int(min_inset + (base_inset - min_inset) * scale)
        spacing = int(min_spacing + (base_spacing - min_spacing) * scale)

        # Apply margins/spacing uniformly
        for gb in [self.model_group, self.config_group, self.info_group, self.rag_group, self.docs_group]:
            lay = gb.layout()
            if isinstance(lay, QVBoxLayout):
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

        rag_panel_parent = self.rag_group.parentWidget()
        if rag_panel_parent is not None:
            rag_panel_layout = rag_panel_parent.layout()
            if isinstance(rag_panel_layout, QVBoxLayout):
                rag_panel_layout.setSpacing(spacing)

        # Clamp info height to ~2 lines of text + insets
        fm = self.info_group.fontMetrics()
        two_lines = 2 * fm.lineSpacing() + inset * 2 + 8
        self.info_group.setMaximumHeight(two_lines)

        # Recompute after densifying
        fixed_height_after = sum(gb.sizeHint().height() for gb in fixed_groups)
        inter_group_gaps_after = spacing * num_gaps
        remaining = available_height - (fixed_height_after + frame_overhead + outer_gutters + inter_group_gaps_after)

        # Allow docs list to be more flexible, but leave room for buttons
        # The Documents group needs space for: list + 2 button rows (~80px) + margins
        button_rows_height = 90
        min_docs = 60
        max_docs = 160
        
        # Calculate available space for list only (subtract button rows)
        list_budget = max(min_docs, remaining - button_rows_height)
        docs_height = max(min_docs, min(max_docs, list_budget))
        
        self.docs_list.setMaximumHeight(docs_height)
        self.docs_list.setMinimumHeight(min_docs)


