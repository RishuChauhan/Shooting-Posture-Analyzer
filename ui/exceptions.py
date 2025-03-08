class AppError(Exception):
    """Base exception class for application errors."""
    
    def __init__(self, message, details=None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Optional details about the error
        """
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        """String representation of the error."""
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message

class DatabaseError(AppError):
    """Exception raised for database-related errors."""
    pass

class VideoError(AppError):
    """Exception raised for video capture and processing errors."""
    pass

class PostureAnalysisError(AppError):
    """Exception raised for errors in posture analysis."""
    pass

class UserProfileError(AppError):
    """Exception raised for errors related to user profiles."""
    pass

class SessionError(AppError):
    """Exception raised for errors related to sessions."""
    pass

class ReportGenerationError(AppError):
    """Exception raised for errors in report generation."""
    pass

class ConfigurationError(AppError):
    """Exception raised for errors in application configuration."""
    pass

class FileSystemError(AppError):
    """Exception raised for file system access errors."""
    pass

def format_exception(exception):
    """
    Format an exception into a user-friendly message.
    
    Args:
        exception: The exception object
        
    Returns:
        User-friendly error message
    """
    if isinstance(exception, AppError):
        return str(exception)
    
    # Format built-in exceptions
    if isinstance(exception, FileNotFoundError):
        return f"File not found: {exception.filename}"
    
    if isinstance(exception, PermissionError):
        return "Permission denied. You may not have the necessary access rights."
    
    if isinstance(exception, ConnectionError):
        return "Network connection error. Please check your connection."
    
    if isinstance(exception, TimeoutError):
        return "Operation timed out. Please try again."
    
    # Default message for unknown exceptions
    return f"An error occurred: {str(exception)}"

def handle_exception(exception, logger):
    """
    Handle and log an exception.
    
    Args:
        exception: The exception object
        logger: Logger instance for logging the error
        
    Returns:
        User-friendly error message
    """
    # Log the exception
    if isinstance(exception, AppError):
        logger.error(f"{exception.__class__.__name__}: {str(exception)}")
    else:
        logger.exception("Unhandled exception")
    
    # Return user-friendly message
    return format_exception(exception)

def wrap_database_errors(func):
    """
    Decorator to wrap database errors in DatabaseError.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, DatabaseError):
                raise
            raise DatabaseError(f"Database operation failed", str(e))
    return wrapper

def wrap_video_errors(func):
    """
    Decorator to wrap video processing errors in VideoError.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, VideoError):
                raise
            raise VideoError(f"Video operation failed", str(e))
    return wrapper

def wrap_analysis_errors(func):
    """
    Decorator to wrap analysis errors in PostureAnalysisError.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, PostureAnalysisError):
                raise
            raise PostureAnalysisError(f"Posture analysis failed", str(e))
    return wrapper

def wrap_report_errors(func):
    """
    Decorator to wrap report generation errors in ReportGenerationError.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if isinstance(e, ReportGenerationError):
                raise
            raise ReportGenerationError(f"Report generation failed", str(e))
    return wrapper