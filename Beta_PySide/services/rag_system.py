"""
Advanced RAG System with Embeddings and Multi-format Document Support
"""
import os
import json
import numpy as np
from typing import List, Dict, Any
from pathlib import Path

try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

# Document parsers
try:
    import pypdf
    HAS_PDF = True
except ImportError:
    HAS_PDF = False

try:
    from docx import Document
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    from bs4 import BeautifulSoup
    import markdown
    HAS_HTML = True
except ImportError:
    HAS_HTML = False

__all__ = [
    "get_rag_system"
]


class DocumentProcessor:
    """Handles multiple document formats"""
    
    @staticmethod
    def process_file(file_path: str) -> str:
        """Extract text from various file formats"""
        path = Path(file_path)
        extension = path.suffix.lower()
        
        try:
            if extension == '.txt':
                return DocumentProcessor._read_txt(file_path)
            elif extension == '.pdf' and HAS_PDF:
                return DocumentProcessor._read_pdf(file_path)
            elif extension in ['.docx', '.doc'] and HAS_DOCX:
                return DocumentProcessor._read_docx(file_path)
            elif extension in ['.html', '.htm'] and HAS_HTML:
                return DocumentProcessor._read_html(file_path)
            elif extension == '.md' and HAS_HTML:
                return DocumentProcessor._read_markdown(file_path)
            else:
                return f"Unsupported file format: {extension}"
        except Exception as e:
            return f"Error processing {path.name}: {str(e)}"
    
    @staticmethod
    def _read_txt(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    @staticmethod
    def _read_pdf(file_path: str) -> str:
        text = ""
        with open(file_path, 'rb') as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    
    @staticmethod
    def _read_docx(file_path: str) -> str:
        doc = Document(file_path)
        return "\n".join([paragraph.text for paragraph in doc.paragraphs])
    
    @staticmethod
    def _read_html(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            return soup.get_text()
    
    @staticmethod
    def _read_markdown(file_path: str) -> str:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            md_content = f.read()
            html = markdown.markdown(md_content)
            soup = BeautifulSoup(html, 'html.parser')
            return soup.get_text()


class EmbeddingRAG:
    """Advanced RAG system with embeddings and semantic search"""
    
    def __init__(self, data_dir: str = "rag_data"):
        self.data_dir = data_dir
        self.documents = []
        self.embeddings = None
        self.index = None
        self.model = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the RAG system"""
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Check for required dependencies
        if not HAS_FAISS:
            print("Warning: FAISS not available. Install with: pip install faiss-cpu")
            return
        
        if not HAS_SENTENCE_TRANSFORMERS:
            print("Warning: sentence-transformers not available. Install with: pip install sentence-transformers")
            return
        
        # Load lightweight embedding model
        try:
            print("Loading embedding model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Embedding model loaded!")
        except Exception as e:
            print(f"Error loading embedding model: {e}")
            return
        
        # Load existing data
        self._load_data()
    
    def add_document(self, file_path: str, chunk_size: int = 500) -> bool:
        """Add a document to the RAG system"""
        if not self.model or not HAS_FAISS or not HAS_SENTENCE_TRANSFORMERS:
            return False
            
        try:
            # Process document
            content = DocumentProcessor.process_file(file_path)
            if content.startswith("Error") or content.startswith("Unsupported"):
                print(content)
                return False
            
            # Chunk the document
            chunks = self._chunk_text(content, chunk_size)
            filename = os.path.basename(file_path)
            
            # Create document entries
            new_docs = []
            for i, chunk in enumerate(chunks):
                doc_entry = {
                    'id': len(self.documents) + len(new_docs),
                    'filename': filename,
                    'chunk_id': i,
                    'content': chunk,
                    'source': file_path
                }
                new_docs.append(doc_entry)
            
            # Generate embeddings for new chunks
            chunk_texts = [doc['content'] for doc in new_docs]
            new_embeddings = self.model.encode(chunk_texts)
            
            # Update storage
            self.documents.extend(new_docs)
            
            if self.embeddings is None:
                self.embeddings = new_embeddings
            else:
                self.embeddings = np.vstack([self.embeddings, new_embeddings])
            
            # Rebuild FAISS index
            self._rebuild_index()
            
            # Save data
            self._save_data()
            
            print(f"Added {len(chunks)} chunks from {filename}")
            return True
            
        except Exception as e:
            print(f"Error adding document: {e}")
            return False
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant documents"""
        if not self.model or not HAS_FAISS or not HAS_SENTENCE_TRANSFORMERS or self.index is None or len(self.documents) == 0:
            return []
        
        try:
            # Encode query
            query_embedding = self.model.encode([query])
            
            # Search
            scores, indices = self.index.search(query_embedding.astype('float32'), min(top_k, len(self.documents)))
            
            # Return results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.documents):
                    result = self.documents[idx].copy()
                    result['similarity_score'] = float(score)
                    results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Search error: {e}")
            return []
    
    def get_context(self, query: str, max_tokens: int = 1000) -> str:
        """Get relevant context for a query"""
        results = self.search(query, top_k=5)
        
        if not results:
            return ""
        
        context_parts = []
        total_length = 0
        
        for result in results:
            content = result['content']
            source = f"[{result['filename']}]"
            
            chunk = f"{source}: {content}"
            
            if total_length + len(chunk) > max_tokens:
                break
                
            context_parts.append(chunk)
            total_length += len(chunk)
        
        if context_parts:
            return "\n\n".join(context_parts)
        return ""
    
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into overlapping chunks"""
        words = text.split()
        chunks = []
        overlap = chunk_size // 4  # 25% overlap
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if len(chunk.strip()) > 50:  # Skip very short chunks
                chunks.append(chunk)
        
        return chunks if chunks else [text]  # Return original if no chunks
    
    def _rebuild_index(self):
        """Rebuild the FAISS index"""
        if not HAS_FAISS or self.embeddings is None or len(self.embeddings) == 0:
            return
            
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner product (cosine similarity)
        
        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings.astype('float32'))
        self.index.add(self.embeddings.astype('float32'))
    
    def _save_data(self):
        """Save RAG data to disk"""
        try:
            data = {
                'documents': self.documents,
                'embeddings': self.embeddings.tolist() if self.embeddings is not None else None
            }
            
            with open(os.path.join(self.data_dir, 'rag_data.json'), 'w') as f:
                json.dump(data, f)
                
        except Exception as e:
            print(f"Error saving data: {e}")
    
    def _load_data(self):
        """Load existing RAG data"""
        try:
            data_file = os.path.join(self.data_dir, 'rag_data.json')
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    data = json.load(f)
                
                self.documents = data.get('documents', [])
                embeddings_list = data.get('embeddings')
                
                if embeddings_list:
                    self.embeddings = np.array(embeddings_list)
                    self._rebuild_index()
                    
                print(f"Loaded {len(self.documents)} documents from storage")
                
        except Exception as e:
            print(f"Error loading data: {e}")
    
    def clear_all(self):
        """Clear all documents and embeddings"""
        self.documents = []
        self.embeddings = None
        self.index = None
        
        # Remove data file
        try:
            data_file = os.path.join(self.data_dir, 'rag_data.json')
            if os.path.exists(data_file):
                os.remove(data_file)
        except Exception as e:
            print(f"Error clearing data: {e}")
        
        print("All RAG data cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics"""
        files = set()
        if self.documents:
            files = {doc['filename'] for doc in self.documents}
        
        return {
            'total_documents': len(files),
            'total_chunks': len(self.documents),
            'embedding_model': 'all-MiniLM-L6-v2' if self.model else None,
            'index_ready': self.index is not None
        }

    # ─────────────────────────────── Document Management Helpers ───────────────────────────────
    def get_document_paths(self) -> List[str]:
        """Return a list of unique source file paths currently indexed."""
        if not self.documents:
            return []
        try:
            paths = {doc.get('source') for doc in self.documents if doc.get('source')}
            # Preserve stable ordering for UI
            return sorted(paths)
        except Exception:
            return []

    def remove_document(self, file_path: str) -> bool:
        """Remove all chunks for a specific document source path.

        Returns True if anything was removed, otherwise False.
        """
        if not file_path or not self.documents:
            return False

        # Compute indices to keep (all docs whose source != file_path)
        keep_indices = [i for i, d in enumerate(self.documents) if d.get('source') != file_path]
        if len(keep_indices) == len(self.documents):
            # Nothing to remove
            return False

        # Rebuild documents and embeddings arrays in the same order
        new_documents = [self.documents[i] for i in keep_indices]
        # Re-assign ids to keep alignment obvious
        for new_id, d in enumerate(new_documents):
            d['id'] = new_id

        if self.embeddings is not None and len(self.embeddings) > 0:
            try:
                self.embeddings = self.embeddings[keep_indices]
            except Exception:
                # Fallback: rebuild via vstack if fancy indexing not available
                self.embeddings = np.vstack([self.embeddings[i] for i in keep_indices]) if keep_indices else None
        
        self.documents = new_documents
        
        # Rebuild FAISS index to reflect removals
        if self.documents and self.embeddings is not None and len(self.embeddings) > 0:
            self._rebuild_index()
        else:
            self.index = None

        # Persist updated state
        self._save_data()
        return True


# Global RAG instance
_rag_system = None

def get_rag_system() -> EmbeddingRAG:
    """Get or create the global RAG system instance"""
    global _rag_system
    if _rag_system is None:
        _rag_system = EmbeddingRAG()
    return _rag_system
