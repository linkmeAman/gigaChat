from typing import List, Optional, Tuple
import re
from profanity_check import predict
from transformers import pipeline
from fastapi import UploadFile
import clamd
import aiofiles
import logging

logger = logging.getLogger(__name__)

class ContentModerator:
    def __init__(self):
        # Initialize toxicity classifier
        self.toxicity_classifier = pipeline(
            "text-classification",
            model="martin-ha/toxic-comment-model",
            return_all_scores=True
        )
        
        # Initialize ClamAV client
        self.clam = clamd.ClamdUnixSocket()
        
        # Compile regex patterns for sensitive data
        self.patterns = {
            'email': re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[-. ]?\d{4}[-. ]?\d{4}[-. ]?\d{4}\b'),
            'ssn': re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'),
        }

    async def moderate_text(self, text: str) -> Tuple[bool, List[str]]:
        """
        Moderate text content for toxicity, profanity, and sensitive information.
        Returns (is_safe, reasons) tuple.
        """
        issues = []
        
        # Check for toxicity
        toxicity_scores = self.toxicity_classifier(text)[0]
        for score in toxicity_scores:
            if score['score'] > 0.8:  # High confidence threshold
                issues.append(f"High {score['label']} content detected")
        
        # Check for profanity
        if predict([text])[0] == 1:
            issues.append("Profanity detected")
        
        # Check for sensitive information
        for pattern_name, pattern in self.patterns.items():
            if pattern.search(text):
                issues.append(f"Possible {pattern_name} detected")
        
        is_safe = len(issues) == 0
        return is_safe, issues

    async def moderate_file(self, file: UploadFile) -> Tuple[bool, Optional[str]]:
        """
        Scan file for malware using ClamAV.
        Returns (is_safe, reason) tuple.
        """
        try:
            # Save uploaded file temporarily
            temp_path = f"/tmp/{file.filename}"
            async with aiofiles.open(temp_path, 'wb') as temp_file:
                content = await file.read()
                await temp_file.write(content)
            
            # Scan with ClamAV
            scan_result = self.clam.scan(temp_path)
            
            # Clean up temp file
            import os
            os.remove(temp_path)
            
            if scan_result:
                path, result = scan_result.popitem()
                status, virus_name = result
                if status == 'FOUND':
                    return False, f"Malware detected: {virus_name}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"File moderation error: {str(e)}")
            return False, "Error scanning file"

# Initialize global moderator instance
moderator = ContentModerator()