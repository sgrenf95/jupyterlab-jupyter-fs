# Jupyter Server Configuration with Download Blocking

import time
import logging
from tornado.web import RequestHandler
from jupyterfs.metamanager import MetaManager

# Initialize logger for config loading messages
logger = logging.getLogger('jupyter_server_config')
logger.setLevel(logging.INFO)

class DownloadBlocker(RequestHandler):
    """
    Blocks all file download requests by returning 403 errors for all download attempts.
    """
    
    def prepare(self):
        """Set security headers."""
        self.set_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; object-src 'none';")
        self.set_header('X-Download-Options', 'noopen')
        self.set_header('X-Content-Type-Options', 'nosniff')
    
    def get(self, *args, **kwargs):
        """Block download requests with 403 error."""
        logger.warning(f"DOWNLOAD BLOCKED: {self.request.path}")
        self.set_status(403)
        self.set_header("Content-Type", "application/json")
        self.finish()
    
    def post(self, *args, **kwargs): self.get(*args, **kwargs)
    def put(self, *args, **kwargs): self.get(*args, **kwargs)
    def delete(self, *args, **kwargs): self.get(*args, **kwargs)
    def head(self, *args, **kwargs): self.get(*args, **kwargs)

def hook_extension_loading():
    try:
        import jupyterfs.extension as jfs_ext
        original_load = jfs_ext._load_jupyter_server_extension
        
        def blocking_load(serverapp):
            # Load original extension first
            try:
                result = original_load(serverapp)
            except Exception as e:
                serverapp.log.warning(f"Extension load warning: {e}")
                result = None
            
            # URL patterns that block all download requests
            try:
                web_app = serverapp.web_app
                blocking_patterns = [
                    (r"/files/(.*)", DownloadBlocker),               # Standard Jupyter downloads
                    (r"/api/contents/.*/download", DownloadBlocker), # API downloads
                    (r".*/download/.*", DownloadBlocker),            # Any download URLs
                ]
                web_app.add_handlers(".*$", blocking_patterns)
                serverapp.log.info("Added blocking layer based on URL patterns")
            except Exception as e:
                serverapp.log.error(f"CRITICAL: Could not add download blocking handlers: {e}")
            
            return result
        
        # Replace the extension loading function
        jfs_ext._load_jupyter_server_extension = blocking_load
        
    except Exception as e:
        logger.error(f"CRITICAL: Extension hook failed: {e}")

# Initialize the extension hook
hook_extension_loading()


# Jupyter Server Configuration
c = get_config()

# Enable jupyter-fs extension
c.ServerApp.jpserver_extensions = {"jupyterfs.extension": True}
c.ServerApp.contents_manager_class = MetaManager

# Security settings
c.ServerApp.allow_origin = "*"
c.ServerApp.allow_credentials = True
c.ServerApp.tornado_settings = {
    'headers': {
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; object-src 'none';",
        'X-Download-Options': 'noopen',
        'X-Content-Type-Options': 'nosniff'
    }
}

# Basic settings
c.ServerApp.disable_check_xsrf = False
c.ServerApp.allow_remote_access = True
c.Application.log_level = "INFO"
c.ServerApp.open_browser = False
c.ContentsManager.allow_hidden = False
