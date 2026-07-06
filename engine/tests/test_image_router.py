import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from PIL import Image

# Add src to path if needed, though pytest usually handles it if run as module
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from image_router import SmartImageRouter, ImageClassifier, OCREnsemble

class TestImageRouter(unittest.TestCase):
    def setUp(self):
        self.router = SmartImageRouter(cfg={
            "ocr_engines": ["tesseract"],
            "ocr_confidence_threshold": 70,
            "llm_prompt": "extract text"
        })

    def test_t1_blank_detection(self):
        """T1: Blank image skips OCR and AI escalation."""
        # Create a completely white image
        white_img = Image.fromarray(np.ones((100, 100), dtype=np.uint8) * 255)
        
        result = self.router.route(white_img)
        
        self.assertEqual(result.get("status"), "Skipped (blank)")
        self.assertFalse(result.get("should_escalate_to_ai"))
        self.assertEqual(result.get("details", {}).get("kind"), "blank")

    @patch('image_router.ImagePreprocessor.preprocess')
    @patch('image_router.ImageClassifier.classify')
    @patch('image_router.OCREnsemble.run')
    def test_t2_document_deskew(self, mock_ocr_run, mock_classify, mock_preprocess):
        """T2: Document classified and preprocessed (deskew) called."""
        mock_classify.return_value = 'document'
        mock_preprocess.return_value = (MagicMock(), {"skew_angle": 12.5, "ops_applied": ["deskew"]})
        mock_ocr_run.return_value = {
            "text": "sample",
            "confidence": 85.0,
            "should_escalate_to_ai": False
        }
        
        dummy_img = Image.fromarray(np.zeros((10, 10), dtype=np.uint8))
        result = self.router.route(dummy_img)
        
        # Verify preprocess was called with deskew enabled
        mock_preprocess.assert_called_once()
        _, kwargs = mock_preprocess.call_args
        self.assertTrue(kwargs.get('enable_deskew', True))
        
        # Verify result has info about deskew discount if any, or just returns correct data
        self.assertFalse(result.get("should_escalate_to_ai"))
        self.assertEqual(result.get("status"), "OCREnsemble (document)")

    @patch('image_router.ImageClassifier.classify')
    @patch('image_router.OCREnsemble.run')
    def test_t3_ocr_ensemble_high_confidence(self, mock_ocr_run, mock_classify):
        """T3: High OCR confidence prevents AI escalation."""
        mock_classify.return_value = 'document'
        # Mock OCREnsemble.run to simulate Tesseract returning 85% conf
        mock_ocr_run.return_value = {
            "text": "Hello World",
            "confidence": 85.0,
            "should_escalate_to_ai": False,
            "breakdown": {"engine_conf": 85.0}
        }
        
        dummy_img = Image.fromarray(np.zeros((10, 10), dtype=np.uint8))
        result = self.router.route(dummy_img)
        
        self.assertFalse(result.get("should_escalate_to_ai"))
        self.assertEqual(result.get("content"), "Hello World")
        self.assertEqual(result.get("confidence"), 85.0)

    @patch('image_router.ImageClassifier.classify')
    @patch('image_router.OCREnsemble.run')
    def test_t4_ai_escalation(self, mock_ocr_run, mock_classify):
        """T4: Low confidence or Photo classification triggers AI escalation."""
        # Case 4-A: Low confidence document
        mock_classify.return_value = 'document'
        mock_ocr_run.return_value = {
            "text": "garbled...",
            "confidence": 45.0,
            "should_escalate_to_ai": True
        }
        dummy_img = Image.fromarray(np.zeros((10, 10), dtype=np.uint8))
        result_low_conf = self.router.route(dummy_img)
        self.assertTrue(result_low_conf.get("should_escalate_to_ai"))
        
        # Case 4-B: Photo classification
        mock_classify.return_value = 'photo'
        result_photo = self.router.route(dummy_img)
        self.assertTrue(result_photo.get("should_escalate_to_ai"))
        self.assertEqual(result_photo.get("details", {}).get("kind"), "photo")

if __name__ == '__main__':
    unittest.main()
