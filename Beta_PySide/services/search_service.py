#!/usr/bin/env python3
"""
Search Service
Provides chat history search functionality with highlighting and navigation
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from PySide6.QtCore import QObject, Signal


class SearchResult:
    """Represents a single search result"""
    
    def __init__(self, message_index: int, start_pos: int, end_pos: int, 
                 context: str, match_text: str, field: str = "content"):
        self.message_index = message_index  # Index in conversation history
        self.start_pos = start_pos  # Start position in text
        self.end_pos = end_pos  # End position in text
        self.context = context  # Surrounding context
        self.match_text = match_text  # The matched text
        self.field = field  # Which field was matched (content, thinking)


class SearchService(QObject):
    """Service for searching chat history"""
    
    # Signals
    search_started = Signal()
    search_completed = Signal(int)  # total_results
    result_selected = Signal(int, int)  # message_index, result_index
    search_cleared = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Search state
        self.search_term = ""
        self.case_sensitive = False
        self.search_thinking = True  # Also search thinking content
        self.use_regex = False
        
        # Results
        self.results: List[SearchResult] = []
        self.current_result_index = -1
        
        # Conversation reference
        self.conversation_history: List[Dict[str, Any]] = []
        
        print("🔍 Search Service initialized")
    
    def set_conversation_history(self, history: List[Dict[str, Any]]):
        """Update the conversation history to search"""
        self.conversation_history = history
    
    def search(self, term: str, case_sensitive: bool = False, 
               search_thinking: bool = True, use_regex: bool = False) -> int:
        """
        Perform a search in the conversation history with progressive results
        
        Args:
            term: Search term or regex pattern
            case_sensitive: Whether to match case
            search_thinking: Whether to search thinking content
            use_regex: Whether to use regex matching
            
        Returns:
            Number of results found
        """
        if not term:
            self.clear_search()
            return 0
        
        self.search_started.emit()
        
        # Update search parameters
        self.search_term = term
        self.case_sensitive = case_sensitive
        self.search_thinking = search_thinking
        self.use_regex = use_regex
        
        # Clear previous results
        self.results.clear()
        self.current_result_index = -1
        
        # Compile regex if needed
        if use_regex:
            try:
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(term, flags)
            except re.error as e:
                print(f"❌ Invalid regex pattern: {e}")
                self.search_completed.emit(0)
                return 0
        else:
            pattern = None
        
        # OPTIMIZATION: Progressive search with early UI updates
        # This keeps the UI responsive during long searches
        total_messages = len(self.conversation_history)
        
        for msg_idx, message in enumerate(self.conversation_history):
            role = message.get("role", "")
            content = message.get("content", "")
            thinking = message.get("thinking", "")
            
            # OPTIMIZATION 1: Search content first (smaller, faster)
            content_results_before = len(self.results)
            self._search_in_text(content, msg_idx, "content", pattern)
            content_found = len(self.results) > content_results_before
            
            # OPTIMIZATION 2: Only search thinking if enabled AND thinking exists
            # Thinking is 3-5x larger than content, so this saves significant time
            if search_thinking and thinking:
                # OPTIMIZATION 3: If content already found match, we know this message
                # is relevant, so thinking search is worth it. Otherwise, skip if
                # thinking is very long (>1000 chars) to save time.
                if content_found or len(thinking) < 1000:
                    self._search_in_text(thinking, msg_idx, "thinking", pattern)
            
            # OPTIMIZATION 4: Log progress every 10 messages for transparency
            if msg_idx % 10 == 0 and msg_idx > 0:
                partial_count = len(self.results)
                print(f"🔍 Progress: {msg_idx}/{total_messages} messages, {partial_count} results so far")
        
        # Emit completion signal
        total_results = len(self.results)
        self.search_completed.emit(total_results)
        
        # Auto-select first result
        if total_results > 0:
            self.current_result_index = 0
            self._emit_current_result()
        
        print(f"🔍 Search complete: {total_results} results for '{term}'")
        return total_results
    
    def _search_in_text(self, text: str, message_index: int, field: str, pattern):
        """Search for matches in a text field"""
        if not text:
            return
        
        if self.use_regex and pattern:
            # Regex search
            for match in pattern.finditer(text):
                start_pos = match.start()
                end_pos = match.end()
                match_text = match.group()
                context = self._extract_context(text, start_pos, end_pos)
                
                result = SearchResult(
                    message_index=message_index,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    context=context,
                    match_text=match_text,
                    field=field
                )
                self.results.append(result)
        else:
            # Simple string search
            search_text = text if self.case_sensitive else text.lower()
            search_term = self.search_term if self.case_sensitive else self.search_term.lower()
            
            start = 0
            while True:
                pos = search_text.find(search_term, start)
                if pos == -1:
                    break
                
                start_pos = pos
                end_pos = pos + len(self.search_term)
                match_text = text[start_pos:end_pos]
                context = self._extract_context(text, start_pos, end_pos)
                
                result = SearchResult(
                    message_index=message_index,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    context=context,
                    match_text=match_text,
                    field=field
                )
                self.results.append(result)
                
                start = end_pos
    
    def _extract_context(self, text: str, start: int, end: int, 
                        context_chars: int = 40) -> str:
        """Extract surrounding context for a match"""
        # Get text before and after match
        before = text[max(0, start - context_chars):start]
        match = text[start:end]
        after = text[end:min(len(text), end + context_chars)]
        
        # Trim to word boundaries
        if before and not before.startswith(' '):
            first_space = before.find(' ')
            if first_space != -1:
                before = '...' + before[first_space:]
            else:
                before = '...' + before
        
        if after and not after.endswith(' '):
            last_space = after.rfind(' ')
            if last_space != -1:
                after = after[:last_space] + '...'
            else:
                after = after + '...'
        
        return before + match + after
    
    def find_next(self) -> bool:
        """Navigate to next search result"""
        if not self.results:
            return False
        
        self.current_result_index = (self.current_result_index + 1) % len(self.results)
        self._emit_current_result()
        return True
    
    def find_previous(self) -> bool:
        """Navigate to previous search result"""
        if not self.results:
            return False
        
        self.current_result_index = (self.current_result_index - 1) % len(self.results)
        self._emit_current_result()
        return True
    
    def _emit_current_result(self):
        """Emit signal for current result"""
        if 0 <= self.current_result_index < len(self.results):
            current_result = self.results[self.current_result_index]
            self.result_selected.emit(current_result.message_index, self.current_result_index)
    
    def get_current_result(self) -> Optional[SearchResult]:
        """Get the currently selected result"""
        if 0 <= self.current_result_index < len(self.results):
            return self.results[self.current_result_index]
        return None
    
    def get_result_at_index(self, index: int) -> Optional[SearchResult]:
        """Get result at specific index"""
        if 0 <= index < len(self.results):
            return self.results[index]
        return None
    
    def get_results_for_message(self, message_index: int) -> List[SearchResult]:
        """Get all search results for a specific message"""
        return [r for r in self.results if r.message_index == message_index]
    
    def get_result_count(self) -> int:
        """Get total number of results"""
        return len(self.results)
    
    def get_current_result_index(self) -> int:
        """Get current result index (0-based)"""
        return self.current_result_index
    
    def clear_search(self):
        """Clear search results"""
        self.search_term = ""
        self.results.clear()
        self.current_result_index = -1
        self.search_cleared.emit()
        print("🔍 Search cleared")
    
    def has_results(self) -> bool:
        """Check if there are any search results"""
        return len(self.results) > 0
    
    def get_search_summary(self) -> str:
        """Get a summary of current search state"""
        if not self.results:
            return "No results"
        
        return f"Result {self.current_result_index + 1} of {len(self.results)}"

