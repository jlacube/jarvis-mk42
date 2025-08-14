"""
Simple coverage test for exceptions using normal import
"""

import pytest
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_api_error_coverage():
    """Test APIError directly to get coverage on lines 49-51"""
    # Directly import the exceptions module
    from utils.exceptions import APIError, JarvisError
    
    # Test basic APIError (line 49-51)
    error = APIError("API call failed", "test_service")
    assert str(error) == "API call failed"
    assert error.service == "test_service"
    assert error.status_code is None
    assert isinstance(error, JarvisError)
    
    # Test APIError with status code
    error_with_status = APIError("API error", "service", status_code=404)
    assert error_with_status.status_code == 404
    assert error_with_status.service == "service"
    
    # Test APIError with proper kwargs
    error_with_details = APIError("API error", "service", error_code="TEST", details={"key": "value"})
    assert error_with_details.service == "service"
    assert error_with_details.error_code == "TEST"
    assert error_with_details.details["key"] == "value"


def test_validation_error_fields():
    """Test ValidationError field and value attributes"""
    from utils.exceptions import ValidationError, JarvisError
    
    # Test without field/value
    error1 = ValidationError("Validation failed")
    assert str(error1) == "Validation failed"
    assert error1.field is None
    assert error1.value is None
    assert isinstance(error1, JarvisError)
    
    # Test with field
    error2 = ValidationError("Invalid field", field="username")
    assert error2.field == "username"
    assert error2.value is None
    
    # Test with field and value
    error3 = ValidationError("Invalid value", field="age", value=-5)
    assert error3.field == "age"
    assert error3.value == -5


def test_all_exception_classes():
    """Test all exception classes exist and work"""
    from utils.exceptions import (
        JarvisError, APIError, ValidationError, DatabaseError,
        SessionError, AudioProcessingError, ImageProcessingError,
        VideoProcessingError
    )
    
    # Test all basic exception types
    errors = [
        (DatabaseError, "Database failed"),
        (SessionError, "Session failed"),
        (AudioProcessingError, "Audio failed"),
        (ImageProcessingError, "Image failed"),
        (VideoProcessingError, "Video failed")
    ]
    
    for error_class, message in errors:
        error = error_class(message)
        assert str(error) == message
        assert isinstance(error, JarvisError)


if __name__ == "__main__":
    test_api_error_coverage()
    test_validation_error_fields()
    test_all_exception_classes()
    print("All tests passed!")
