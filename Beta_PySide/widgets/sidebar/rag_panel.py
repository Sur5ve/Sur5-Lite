#!/usr/bin/env python3
"""
RAG Panel
UI panel for document upload and RAG management
"""

import os
from typing import List, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QListWidget, QListWidgetItem,
    QFileDialog, QCheckBox, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, Slot

from services.document_service import DocumentService


class RAGPanel(QWidget):
    """Panel for RAG document management"""
    
    def __init__(self, document_service: DocumentService, parent=None):
        super().__init__(parent)
        
        # Service reference
        self.document_service = document_service
        
        # UI components
        self.rag_enabled_checkbox: Optional[QCheckBox] = None
        self.document_list: Optional[QListWidget] = None
        self.upload_button: Optional[QPushButton] = None
        self.remove_button: Optional[QPushButton] = None
        self.clear_button: Optional[QPushButton] = None
        self.status_label: Optional[QLabel] = None
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._update_ui_state()
        
    def _setup_ui(self):
        """Setup the RAG panel UI"""
        # Main layout - zero margins/spacing; ResponsiveSidebar will manage
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # RAG control group
        control_group = QGroupBox("RAG System")
        control_layout = QVBoxLayout(control_group)
        control_layout.setSpacing(12)
        control_layout.setContentsMargins(12, 12, 12, 12)
        
        # RAG enabled checkbox
        self.rag_enabled_checkbox = QCheckBox("Enable RAG")
        self.rag_enabled_checkbox.setAccessibleName("Enable RAG")
        self.rag_enabled_checkbox.setChecked(True)
        self.rag_enabled_checkbox.toggled.connect(self._on_rag_toggle)
        control_layout.addWidget(self.rag_enabled_checkbox)
        
        # Status label
        self.status_label = QLabel("RAG enabled - 0 documents")
        self.status_label.setAccessibleName("RAG status")
        self.status_label.setStyleSheet("color: #888888; font-size: 11px;")
        control_layout.addWidget(self.status_label)
        
        main_layout.addWidget(control_group)
        
        # Documents group
        docs_group = QGroupBox("Documents")
        docs_layout = QVBoxLayout(docs_group)
        docs_layout.setSpacing(12)
        docs_layout.setContentsMargins(12, 12, 12, 12)
        
        # Document list
        self.document_list = QListWidget()
        self.document_list.setAccessibleName("Documents list")
        self.document_list.setMaximumHeight(170)
        self.document_list.setAlternatingRowColors(True)
        self.document_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.document_list.setWordWrap(False)
        try:
            from PySide6.QtCore import Qt as _Qt
            self.document_list.setTextElideMode(_Qt.TextElideMode.ElideMiddle)
        except Exception:
            pass
        self.document_list.setUniformItemSizes(True)
        self.document_list.itemSelectionChanged.connect(self._on_selection_changed)
        docs_layout.addWidget(self.document_list)
        
        # Document buttons row (simple layout)
        doc_button_layout = QHBoxLayout()
        doc_button_layout.setContentsMargins(0, 0, 0, 0)
        doc_button_layout.setSpacing(8)

        self.upload_button = QPushButton("Upload")
        self.upload_button.setAccessibleName("Upload documents")
        self.upload_button.setProperty("class", "primary")
        self.upload_button.setMinimumHeight(34)
        self.upload_button.clicked.connect(self._upload_document)
        doc_button_layout.addWidget(self.upload_button)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setAccessibleName("Remove selected document")
        self.remove_button.setProperty("class", "danger")
        self.remove_button.setMinimumHeight(34)
        self.remove_button.clicked.connect(self._remove_document)
        self.remove_button.setEnabled(False)
        doc_button_layout.addWidget(self.remove_button)

        docs_layout.addLayout(doc_button_layout)
        
        # Clear all button row (simple layout)
        self.clear_button = QPushButton("Clear All")
        self.clear_button.setAccessibleName("Clear all documents")
        self.clear_button.setProperty("class", "danger")
        self.clear_button.setMinimumHeight(34)
        self.clear_button.clicked.connect(self._clear_all_documents)
        self.clear_button.setEnabled(False)
        clear_layout = QHBoxLayout()
        clear_layout.setContentsMargins(0, 0, 0, 0)
        clear_layout.setSpacing(8)
        clear_layout.addWidget(self.clear_button)
        clear_layout.addStretch(1)
        docs_layout.addLayout(clear_layout)
        
        main_layout.addWidget(docs_group)
        
        # RAG Information moved to menu dialog. Keep group hidden to reduce sidebar height.
        info_group = QGroupBox("RAG Information")
        info_group.setVisible(False)
        
        # No stretch - ResponsiveSidebar manages spacing
        
    def _connect_signals(self):
        """Connect document service signals"""
        self.document_service.document_added.connect(self._on_document_added)
        self.document_service.document_removed.connect(self._on_document_removed)
        self.document_service.rag_status_changed.connect(self._on_rag_status_changed)
        self.document_service.processing_started.connect(self._on_processing_started)
        self.document_service.processing_finished.connect(self._on_processing_finished)
        self.document_service.error_occurred.connect(self._on_error_occurred)
        
    def _upload_document(self):
        """Upload a document to the RAG system"""
        file_dialog = QFileDialog()
        file_dialog.setNameFilter(
            "Documents (*.txt *.pdf *.docx *.doc *.html *.htm *.md);;All files (*)"
        )
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)  # Allow multiple files
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            
            for file_path in selected_files:
                if self.document_service.is_file_supported(file_path):
                    # Disable upload button during processing
                    self.upload_button.setEnabled(False)
                    self.upload_button.setText("Processing...")
                    
                    # Add document
                    success = self.document_service.add_document(file_path)
                    
                    # Re-enable button
                    self.upload_button.setEnabled(True)
                    self.upload_button.setText("Upload")
                    
                    if not success:
                        QMessageBox.warning(
                            self,
                            "Upload Failed",
                            f"Failed to upload {os.path.basename(file_path)}"
                        )
                else:
                    QMessageBox.warning(
                        self,
                        "Unsupported Format",
                        f"File format not supported: {os.path.basename(file_path)}"
                    )
                    
    def _remove_document(self):
        """Remove selected document"""
        current_item = self.document_list.currentItem()
        if current_item:
            document_name = current_item.text()
            
            # Find the full path
            document_paths = self.document_service.get_document_paths()
            document_path = None
            
            for path in document_paths:
                if os.path.basename(path) == document_name:
                    document_path = path
                    break
                    
            if document_path:
                # Confirm removal
                reply = QMessageBox.question(
                    self,
                    "Remove Document",
                    f"Are you sure you want to remove '{document_name}' from the RAG system?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    success = self.document_service.remove_document(document_path)
                    if not success:
                        QMessageBox.warning(
                            self,
                            "Remove Failed",
                            f"Failed to remove {document_name}"
                        )
                        
    def _clear_all_documents(self):
        """Clear all documents"""
        if self.document_list.count() > 0:
            reply = QMessageBox.question(
                self,
                "Clear All Documents",
                "Are you sure you want to remove all documents from the RAG system?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.document_service.clear_all_documents()
                
    def _on_rag_toggle(self, enabled: bool):
        """Handle RAG enabled toggle"""
        self.document_service.set_rag_enabled(enabled)
        
        # Update UI state
        self.document_list.setEnabled(enabled)
        self.upload_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled and self.document_list.currentItem() is not None)
        self.clear_button.setEnabled(enabled and self.document_list.count() > 0)
        
    def _on_selection_changed(self):
        """Handle document list selection change"""
        has_selection = self.document_list.currentItem() is not None
        rag_enabled = self.rag_enabled_checkbox.isChecked()
        self.remove_button.setEnabled(rag_enabled and has_selection)
        
    @Slot(str)
    def _on_document_added(self, document_name: str):
        """Handle document added event"""
        self._refresh_document_list()
        
    @Slot(str)
    def _on_document_removed(self, document_name: str):
        """Handle document removed event"""
        self._refresh_document_list()
        
    @Slot(bool, int)
    def _on_rag_status_changed(self, enabled: bool, doc_count: int):
        """Handle RAG status change"""
        status_text = f"RAG {'enabled' if enabled else 'disabled'} - {doc_count} documents"
        self.status_label.setText(status_text)
        
        if enabled:
            self.status_label.setStyleSheet("color: #27ae60; font-size: 11px; font-weight: bold;")
        else:
            self.status_label.setStyleSheet("color: #888888; font-size: 11px;")
            
        # Update clear button state
        rag_enabled = self.rag_enabled_checkbox.isChecked()
        self.clear_button.setEnabled(rag_enabled and doc_count > 0)
        
    @Slot(str)
    def _on_processing_started(self, document_name: str):
        """Handle processing started"""
        self.status_label.setText(f"Processing {document_name}...")
        self.status_label.setStyleSheet("color: #3498db; font-size: 11px;")
        
    @Slot(str, bool)
    def _on_processing_finished(self, document_name: str, success: bool):
        """Handle processing finished"""
        if success:
            self.status_label.setText(f"✅ Added {document_name}")
            self.status_label.setStyleSheet("color: #27ae60; font-size: 11px;")
        else:
            self.status_label.setText(f"❌ Failed to add {document_name}")
            self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px;")
            
        # Reset status after a delay
        QWidget().startTimer(3000)  # Will reset via _update_ui_state
        
    @Slot(str)
    def _on_error_occurred(self, error_message: str):
        """Handle error event"""
        self.status_label.setText(f"❌ Error: {error_message}")
        self.status_label.setStyleSheet("color: #e74c3c; font-size: 11px; font-weight: bold;")
        
    def _refresh_document_list(self):
        """Refresh the document list"""
        self.document_list.clear()
        
        document_names = self.document_service.get_document_list()
        for doc_name in document_names:
            item = QListWidgetItem(doc_name)
            self.document_list.addItem(item)
            
        # Update button states
        self._on_selection_changed()
        
    def _update_ui_state(self):
        """Update UI state based on document service"""
        # Update RAG enabled checkbox
        rag_enabled = self.document_service.is_rag_enabled()
        self.rag_enabled_checkbox.setChecked(rag_enabled)
        
        # Refresh document list
        self._refresh_document_list()
        
        # Update status
        stats = self.document_service.get_rag_stats()
        doc_count = stats.get('total_documents', 0)
        enabled = stats.get('rag_enabled', True)
        
        status_text = f"RAG {'enabled' if enabled else 'disabled'} - {doc_count} documents"
        self.status_label.setText(status_text)
        
    def get_document_count(self) -> int:
        """Get current document count"""
        return self.document_list.count()
        
    def is_rag_enabled(self) -> bool:
        """Check if RAG is enabled"""
        return self.rag_enabled_checkbox.isChecked()
