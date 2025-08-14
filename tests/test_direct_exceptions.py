"""
Direct tests for exceptions module to achieve 100% coverage
"""

import pytest


class TestExceptionsDirectCoverage:
    """Test exceptions module directly without utils.__init__ import chain"""
    
    def test_direct_import_all_exceptions(self):
        """Test direct import of all exception classes"""
        # Import directly from the module file to avoid utils.__init__ chain
        import sys
        import importlib.util
        spec = importlib.util.spec_from_file_location("exceptions", "utils/exceptions.py")
        exceptions_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exceptions_module)
        
        # Test all the main exception classes
        JarvisError = exceptions_module.JarvisError
        APIError = exceptions_module.APIError
        ValidationError = exceptions_module.ValidationError
        DatabaseError = exceptions_module.DatabaseError
        SessionError = exceptions_module.SessionError
        AudioProcessingError = exceptions_module.AudioProcessingError
        ImageProcessingError = exceptions_module.ImageProcessingError
        VideoProcessingError = exceptions_module.VideoProcessingError
        
        # Test APIError (lines 49-51 that were missing coverage)
        api_error = APIError("API call failed", "test_service")
        assert str(api_error) == "API call failed"
        assert api_error.service == "test_service"
        assert api_error.status_code is None
        assert isinstance(api_error, JarvisError)
        
        # Test APIError with status code
        api_error_with_status = APIError("API error", "service", status_code=404)
        assert api_error_with_status.status_code == 404
        assert api_error_with_status.service == "service"
        
        # Test APIError with details (using proper JarvisError kwargs)
        api_error_kwargs = APIError("API error", "service", status_code=500, error_code="API_ERROR", details={"extra": "data"})
        assert api_error_kwargs.service == "service"
        assert api_error_kwargs.status_code == 500
        assert api_error_kwargs.error_code == "API_ERROR"
        assert api_error_kwargs.details["extra"] == "data"
    
    def test_validation_error_with_fields(self):
        """Test ValidationError with field and value parameters"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("exceptions", "utils/exceptions.py")
        exceptions_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exceptions_module)
        
        ValidationError = exceptions_module.ValidationError
        JarvisError = exceptions_module.JarvisError
        
        # Test ValidationError without field/value
        error1 = ValidationError("Validation failed")
        assert str(error1) == "Validation failed"
        assert error1.field is None
        assert error1.value is None
        assert isinstance(error1, JarvisError)
        
        # Test ValidationError with field
        error2 = ValidationError("Invalid field", field="username")
        assert error2.field == "username"
        assert error2.value is None
        
        # Test ValidationError with field and value
        error3 = ValidationError("Invalid value", field="age", value=-5)
        assert error3.field == "age"
        assert error3.value == -5
    
    def test_all_specific_errors(self):
        """Test all specific error types"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("exceptions", "utils/exceptions.py")
        exceptions_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exceptions_module)
        
        JarvisError = exceptions_module.JarvisError
        
        # Test all error types
        error_classes = [
            (exceptions_module.DatabaseError, "Database failed"),
            (exceptions_module.SessionError, "Session failed"),
            (exceptions_module.AudioProcessingError, "Audio failed"),
            (exceptions_module.ImageProcessingError, "Image failed"),
            (exceptions_module.VideoProcessingError, "Video failed")
        ]
        
        for error_class, message in error_classes:
            error = error_class(message)
            assert str(error) == message
            assert isinstance(error, JarvisError)
    
    def test_exception_aliases(self):
        """Test that aliases are correctly set up"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("exceptions", "utils/exceptions.py")
        exceptions_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exceptions_module)
        
        # Test aliases
        assert exceptions_module.JarvisValidationError is exceptions_module.ValidationError
        assert exceptions_module.JarvisAPIError is exceptions_module.APIError
        assert exceptions_module.JarvisDatabaseError is exceptions_module.DatabaseError
        
        # Test using aliases
        alias_error = exceptions_module.JarvisAPIError("Test", "service")
        assert isinstance(alias_error, exceptions_module.APIError)
        assert isinstance(alias_error, exceptions_module.JarvisError)
    
    def test_exception_inheritance_chain(self):
        """Test complete inheritance chain"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("exceptions", "utils/exceptions.py")
        exceptions_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exceptions_module)
        
        # Test that all exceptions inherit from JarvisError
        all_errors = [
            exceptions_module.APIError("test", "service"),
            exceptions_module.ValidationError("test"),
            exceptions_module.DatabaseError("test"),
            exceptions_module.SessionError("test"),
            exceptions_module.AudioProcessingError("test"),
            exceptions_module.ImageProcessingError("test"),
            exceptions_module.VideoProcessingError("test")
        ]
        
        for error in all_errors:
            assert isinstance(error, exceptions_module.JarvisError)
            assert isinstance(error, Exception)
            assert str(error) == "test"


if __name__ == "__main__":
    pytest.main([__file__])
