# =============================================================================
# SECURE JUPYTERLAB DOWNLOAD BLOCKING CONFIGURATION
# =============================================================================
# This configuration implements a single-layer download blocking system that
# prevents all file downloads from JupyterLab while maintaining full functionality
# for viewing, editing, and running code.

import time
import logging
from tornado.web import RequestHandler
from jupyterfs.metamanager import MetaManager

# Initialize logger for tracking system behavior
logger = logging.getLogger('jupyter_server_config')
logger.setLevel(logging.INFO)

# =============================================================================
# DOWNLOAD BLOCKING HANDLER
# =============================================================================
class DownloadBlocker(RequestHandler):
    """
    Custom Tornado RequestHandler that intercepts and blocks all download requests.
    
    HOW IT WORKS:
    1. This handler replaces normal file serving handlers
    2. When a download is attempted, it captures the request
    3. Instead of serving the file, it returns a 403 Forbidden error
    4. Logs the blocked attempt for monitoring
    
    WHAT IT BLOCKS:
    - Direct file downloads via /files/* URLs
    - API-based downloads via /api/contents/*/download
    - Any URL pattern containing "download"
    - All HTTP methods (GET, POST, PUT, DELETE, HEAD)
    """
    
    def prepare(self):
        """
        Set security headers for all responses.
        These headers prevent browsers from attempting alternative download methods.
        """
        # Content Security Policy: Restricts resource loading
        self.set_header('Content-Security-Policy', 
                       "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; object-src 'none';")
        # Prevent browsers from auto-opening downloaded files
        self.set_header('X-Download-Options', 'noopen')
        # Prevent MIME type sniffing that could bypass restrictions
        self.set_header('X-Content-Type-Options', 'nosniff')
    
    def get(self, *args, **kwargs):
        """
        Handle GET requests (most common download method).
        Returns 403 Forbidden instead of serving the requested file.
        """
        # Log the blocked attempt with the requested path
        logger.warning(f"DOWNLOAD BLOCKED: {self.request.path}")
        
        # Return 403 Forbidden status
        self.set_status(403)
        self.set_header("Content-Type", "application/json")
        
        # Send error response to browser (visible in Network tab)
        self.write({
            "error": "File downloads are disabled",
            "message": "This JupyterLab instance does not permit file downloads",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "blocked_path": self.request.path
        })
        self.finish()

# =============================================================================
# EXTENSION HOOK - THE CORE BLOCKING MECHANISM
# =============================================================================
def hook_extension_loading():
    """
    This is the heart of the download blocking system.
    
    STRATEGY:
    We intercept the jupyter-fs extension loading process and inject our blocking handlers
    at the web application level.
    
    WHY THIS WORKS:
    1. jupyter-fs handles ALL file operations when loaded (including standard Jupyter files)
    2. By hooking into its loading process, we ensure our blocking happens AFTER
       jupyter-fs is ready but BEFORE it starts serving files
    3. URL patterns at the web app level catch ALL possible download requests
    4. This single interception point blocks both standard Jupyter and S3 downloads
    """
    try:
        # Import the jupyter-fs extension module
        import jupyterfs.extension as jfs_ext
        
        # Store reference to the original extension loading function
        original_load = jfs_ext._load_jupyter_server_extension
        
        def blocking_load(serverapp):
            """
            Custom loading function that wraps the original jupyter-fs loader.
            This function:
            1. Loads jupyter-fs normally (full functionality preserved)
            2. Adds our download blocking URL patterns to the web application
            3. Returns control to Jupyter (system continues normally)
            """
            
            # STEP 1: Load original jupyter-fs extension
            # This ensures all jupyter-fs functionality works normally
            try:
                result = original_load(serverapp)
                serverapp.log.info("jupyter-fs extension loaded successfully")
            except Exception as e:
                serverapp.log.warning(f"Extension load warning: {e}")
                result = None
            
            # STEP 2: Add download blocking URL patterns
            # These patterns intercept download requests BEFORE they reach file handlers
            try:
                web_app = serverapp.web_app
                
                # Define URL patterns that match all possible download requests
                blocking_patterns = [
                    # Standard Jupyter file downloads (e.g., /files/myfile.txt)
                    (r"/files/(.*)", DownloadBlocker),
                    
                    # API-based downloads (e.g., /api/contents/myfile.txt/download)
                    (r"/api/contents/.*/download", DownloadBlocker),
                    
                    # Any URL containing "download" (catches edge cases)
                    (r".*/download/.*", DownloadBlocker),
                ]
                
                # Add these patterns to the web application with highest priority
                # The ".*$" parameter means these patterns apply to all hosts
                web_app.add_handlers(".*$", blocking_patterns)
                
                serverapp.log.info("Download blocking layer active - all downloads will be blocked")
                
            except Exception as e:
                serverapp.log.error(f"CRITICAL: Could not add download blocking handlers: {e}")
            
            # STEP 3: Return the original result to maintain normal Jupyter operation
            return result
        
        # STEP 4: Replace the original extension loading function with our wrapper
        # This means when Jupyter loads jupyter-fs, it actually calls our function
        jfs_ext._load_jupyter_server_extension = blocking_load
        
        logger.info("Successfully hooked into jupyter-fs extension loading")
        
    except Exception as e:
        logger.error(f"CRITICAL: Extension hook failed: {e}")
        logger.error("Download blocking will NOT be active!")

# =============================================================================
# INITIALIZE THE BLOCKING SYSTEM
# =============================================================================
# Execute the hook immediately when this config file is loaded
hook_extension_loading()


# =============================================================================
# JUPYTER SERVER CONFIGURATION
# =============================================================================
# Standard Jupyter configuration with security-focused settings

# Get the configuration object
c = get_config()

# =============================================================================
# EXTENSION CONFIGURATION
# =============================================================================
# Enable jupyter-fs extension for S3 and filesystem browsing
c.ServerApp.jpserver_extensions = {"jupyterfs.extension": True}

# Use MetaManager for handling multiple filesystem backends
# This allows jupyter-fs to manage both local files and S3 buckets
c.ServerApp.contents_manager_class = MetaManager

# =============================================================================
# SECURITY SETTINGS
# =============================================================================
# Configure CORS and security headers

# Allow connections from any origin (adjust for production environments)
c.ServerApp.allow_origin = "*"
c.ServerApp.allow_credentials = True

# Set security headers at the application level
# These work in conjunction with the headers set in DownloadBlocker
c.ServerApp.tornado_settings = {
    'headers': {
        # Content Security Policy: Restricts resource loading and execution
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; object-src 'none';",
        
        # Prevent browsers from automatically opening downloaded files
        'X-Download-Options': 'noopen',
        
        # Prevent MIME type sniffing (security protection)
        'X-Content-Type-Options': 'nosniff'
    }
}

# =============================================================================
# APPLICATION SETTINGS
# =============================================================================
# Configure basic Jupyter server behavior

# Enable XSRF protection (Cross-Site Request Forgery)
c.ServerApp.disable_check_xsrf = False

# Allow remote connections (required for Docker deployment)
c.ServerApp.allow_remote_access = True

# Set logging level to INFO for monitoring
c.Application.log_level = "INFO"

# Don't automatically open browser (Docker environment)
c.ServerApp.open_browser = False

# Hide hidden files in file browser (security best practice)
c.ContentsManager.allow_hidden = False
