"""
Quality control system for question-answer pairs
"""

import re
import logging
from typing import Dict, List, Tuple
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QualityController:
    def __init__(self):
        self.garbage_patterns = self._load_garbage_patterns()
    
    def _load_garbage_patterns(self) -> List[str]:
        """Load patterns that indicate low-quality questions"""
        return [
            r'\bwhat does i mean\b',
            r'\bhow do you execute what\b',
            r'\bwhat role does a play\b',
            r'\bwhat aspects of - are\b',
            r'\bwhat is explained about -\b',
            r'\bwhat does that mean\b',
            r'\bhow does it work\b',
            r'\bwhat is the purpose of it\b',
            r'^what is \w+\?$',
            r'^how does \w+ work\?$',
        ]
    
    def assess_question_quality(self, question: str, context: str = "") -> float:
        """
        Assess the quality of a question
        Returns quality score between 0.0 and 1.0
        """
        score = 0.5  # Base score
        
        # Check for garbage patterns
        if self._contains_garbage_patterns(question):
            return 0.0
        
        # Basic format validation
        format_score = self._assess_format_quality(question)
        score += format_score * 0.3
        
        # Content relevance
        relevance_score = self._assess_content_relevance(question)
        score += relevance_score * 0.3
        
        # Business focus
        business_score = self._assess_business_focus(question)
        score += business_score * 0.2
        
        # Complexity appropriateness
        complexity_score = self._assess_complexity_appropriateness(question)
        score += complexity_score * 0.2
        
        return min(1.0, max(0.0, score))
    
    def _contains_garbage_patterns(self, question: str) -> bool:
        """Check if question contains garbage patterns"""
        question_lower = question.lower()
        
        for pattern in self.garbage_patterns:
            if re.search(pattern, question_lower):
                return True
        
        return False
    
    def _assess_format_quality(self, question: str) -> float:
        """Assess basic format quality of question"""
        score = 0.0
        
        # Proper capitalization
        if question and question[0].isupper():
            score += 0.3
        
        # Ends with question mark
        if question.endswith('?'):
            score += 0.4
        
        # Appropriate length (6-25 words)
        word_count = len(question.split())
        if 6 <= word_count <= 25:
            score += 0.3
        
        return score
    
    def _assess_content_relevance(self, question: str) -> float:
        """Assess content relevance and specificity"""
        score = 0.0
        question_lower = question.lower()
        
        # Check for business/AI keywords
        business_keywords = [
            'revenue', 'business', 'strategy', 'consulting', 'automation',
            'AI', 'client', 'service', 'process', 'optimization', 'growth'
        ]
        
        matches = sum(1 for keyword in business_keywords if keyword in question_lower)
        
        if matches >= 2:
            score += 0.5
        elif matches == 1:
            score += 0.3
        
        # Avoid overly generic questions
        if not question_lower.startswith(('what is', 'how does')):
            score += 0.2
        
        return min(1.0, score)
    
    def _assess_business_focus(self, question: str) -> float:
        """Assess how well the question focuses on business aspects"""
        question_lower = question.lower()
        
        business_indicators = [
            'revenue', 'profit', 'ROI', 'growth', 'strategy',
            'client', 'customer', 'service', 'consulting',
            'implementation', 'optimization', 'results'
        ]
        
        matches = sum(1 for indicator in business_indicators if indicator in question_lower)
        
        if matches >= 2:
            return 1.0
        elif matches == 1:
            return 0.6
        else:
            return 0.0
    
    def _assess_complexity_appropriateness(self, question: str) -> float:
        """Assess if question complexity is appropriate"""
        word_count = len(question.split())
        
        # Optimal complexity range
        if 8 <= word_count <= 18:
            return 1.0
        elif 6 <= word_count <= 22:
            return 0.7
        else:
            return 0.3
