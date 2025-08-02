package middleware

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// ErrorResponse represents a standardized error response
type ErrorResponse struct {
	Error   string `json:"error"`
	Message string `json:"message"`
	Code    int    `json:"code"`
}

// ErrorHandler creates an error handling middleware
func ErrorHandler() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Next()

		// Handle any errors that occurred during request processing
		if len(c.Errors) > 0 {
			err := c.Errors.Last()
			
			// Log the error
			LogError("error_handler", "Request processing error", err.Err)

			// Determine status code based on error type
			statusCode := http.StatusInternalServerError
			message := "Internal server error"

			switch err.Type {
			case gin.ErrorTypeBind:
				statusCode = http.StatusBadRequest
				message = "Invalid request format"
			case gin.ErrorTypePublic:
				statusCode = http.StatusBadRequest
				message = err.Error()
			case gin.ErrorTypeRender:
				statusCode = http.StatusInternalServerError
				message = "Response rendering error"
			}

			// Don't override if status was already set
			if c.Writer.Status() != http.StatusOK {
				statusCode = c.Writer.Status()
			}

			// Send error response if not already sent
			if !c.Writer.Written() {
				c.JSON(statusCode, ErrorResponse{
					Error:   http.StatusText(statusCode),
					Message: message,
					Code:    statusCode,
				})
			}
		}
	}
}

// AbortWithError is a helper function to abort with a specific error
func AbortWithError(c *gin.Context, statusCode int, message string) {
	c.JSON(statusCode, ErrorResponse{
		Error:   http.StatusText(statusCode),
		Message: message,
		Code:    statusCode,
	})
	c.Abort()
}