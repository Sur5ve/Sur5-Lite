#!/usr/bin/env python3
"""
Document Service
High-level service for RAG document management with Qt integration
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from .rag_system import get_rag_system


class DocumentService(QObject):
    """Service for managing documents and RAG functionality"""
    
    # Signals
    document_added = Signal(str)  # document_name
    document_removed = Signal(str)  # document_name
    rag_status_changed = Signal(bool, int)  # enabled, doc_count
    processing_started = Signal(str)  # document_name
    processing_finished = Signal(str, bool)  # document_name, success
    error_occurred = Signal(str)  # error_message
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get RAG system instance
        self.rag_system = get_rag_system()
        self.rag_enabled = True
        
        # Supported file extensions
        self.supported_extensions = {
            '.txt', '.pdf', '.docx', '.doc', '.html', '.htm', '.md'
        }
        
        print("📚 Document Service initialized")
        
    def add_document(self, file_path: str, chunk_size: int = 500) -> bool:
        """Add a document to the RAG system"""
        try:
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                self.error_occurred.emit(error_msg)
                return False
                
            # Check file extension
            file_ext = Path(file_path).suffix.lower()
            if file_ext not in self.supported_extensions:
                error_msg = f"Unsupported file type: {file_ext}"
                self.error_occurred.emit(error_msg)
                return False
                
            document_name = os.path.basename(file_path)
            
            # Emit processing started
            self.processing_started.emit(document_name)
            
            # Add to RAG system
            success = self.rag_system.add_document(file_path, chunk_size)
            
            # Emit processing finished
            self.processing_finished.emit(document_name, success)
            
            if success:
                # Emit document added and status change
                self.document_added.emit(document_name)
                doc_count = len(self.get_document_list())
                self.rag_status_changed.emit(self.rag_enabled, doc_count)
                
                print(f"📄 Document added: {document_name}")
                return True
            else:
                error_msg = f"Failed to add document: {document_name}"
                self.error_occurred.emit(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Error adding document: {str(e)}"
            self.error_occurred.emit(error_msg)
            print(f"❌ {error_msg}")
            return False
            
    def remove_document(self, file_path: str) -> bool:
        """Remove a document from the RAG system"""
        try:
            document_name = os.path.basename(file_path)
            
            # Remove from RAG system
            success = self.rag_system.remove_document(file_path)
            
            if success:
                # Emit document removed and status change
                self.document_removed.emit(document_name)
                doc_count = len(self.get_document_list())
                self.rag_status_changed.emit(self.rag_enabled, doc_count)
                
                print(f"🗑️ Document removed: {document_name}")
                return True
            else:
                error_msg = f"Document not found or failed to remove: {document_name}"
                self.error_occurred.emit(error_msg)
                return False
                
        except Exception as e:
            error_msg = f"Error removing document: {str(e)}"
            self.error_occurred.emit(error_msg)
            print(f"❌ {error_msg}")
            return False
            
    def get_document_list(self) -> List[str]:
        """Get list of currently loaded documents"""
        try:
            paths = self.rag_system.get_document_paths()
            return [os.path.basename(path) for path in paths]
        except Exception as e:
            print(f"❌ Error getting document list: {e}")
            return []
            
    def get_document_paths(self) -> List[str]:
        """Get list of full document paths"""
        try:
            return self.rag_system.get_document_paths()
        except Exception as e:
            print(f"❌ Error getting document paths: {e}")
            return []
            
    def search_documents(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search documents for relevant content"""
        if not self.rag_enabled:
            return []
            
        try:
            return self.rag_system.search(query, top_k)
        except Exception as e:
            print(f"❌ Error searching documents: {e}")
            return []
            
    def get_context_for_query(self, query: str, max_tokens: int = 1000) -> str:
        """Get relevant context for a query"""
        if not self.rag_enabled:
            return ""
            
        try:
            return self.rag_system.get_context(query, max_tokens)
        except Exception as e:
            print(f"❌ Error getting context: {e}")
            return ""
            
    def get_rag_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        try:
            stats = self.rag_system.get_stats()
            stats['rag_enabled'] = self.rag_enabled
            return stats
        except Exception as e:
            print(f"❌ Error getting RAG stats: {e}")
            return {
                'total_documents': 0,
                'total_chunks': 0,
                'embedding_model': None,
                'index_ready': False,
                'rag_enabled': self.rag_enabled
            }
            
    def set_rag_enabled(self, enabled: bool):
        """Enable or disable RAG functionality"""
        if self.rag_enabled != enabled:
            self.rag_enabled = enabled
            doc_count = len(self.get_document_list()) if enabled else 0
            self.rag_status_changed.emit(enabled, doc_count)
            
            status = "enabled" if enabled else "disabled"
            print(f"🔄 RAG {status}")
            
    def is_rag_enabled(self) -> bool:
        """Check if RAG is enabled"""
        return self.rag_enabled
        
    def clear_all_documents(self):
        """Clear all documents from the RAG system"""
        try:
            self.rag_system.clear_all()
            self.rag_status_changed.emit(self.rag_enabled, 0)
            print("🗑️ All documents cleared")
        except Exception as e:
            error_msg = f"Error clearing documents: {str(e)}"
            self.error_occurred.emit(error_msg)
            print(f"❌ {error_msg}")
            
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions"""
        return sorted(list(self.supported_extensions))
        
    def is_file_supported(self, file_path: str) -> bool:
        """Check if a file type is supported"""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.supported_extensions
