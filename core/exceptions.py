# Exception classes cho AI Agent
class AIAgentException(Exception):
    """Base exception class for AI Agent"""
    pass

class DatabaseError(AIAgentException):
    """Database related errors"""
    pass

class TimeParsingError(AIAgentException):
    """Time parsing related errors"""
    pass

class GeminiAPIError(AIAgentException):
    """Gemini API related errors"""
    pass

class GoogleCalendarError(AIAgentException):
    """Google Calendar sync errors"""
    pass

class ValidationError(AIAgentException):
    """Input validation errors"""
    pass
