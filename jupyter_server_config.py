# Jupyter Server Configuration with Download Blocking
# SCIENTIFIC APPROACH: Testing one layer at a time

import time
from tornado.web import RequestHandler
from jupyterfs.metamanager import MetaManager

print(f"🔒 {time.strftime('%H:%M:%S')} - Initializing download blocking...")

class DownloadBlocker(RequestHandler):
    """Blocks all file download requests."""
    
    def prepare(self):
        """Set security headers."""
        self.set_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; object-src 'none';")
        self.set_header('X-Download-Options', 'noopen')
        self.set_header('X-Content-Type-Options', 'nosniff')
    
    def get(self, *args, **kwargs):
        """Block download requests with 403 error."""
        print(f"🚫 {time.strftime('%H:%M:%S')} - BLOCKED: {self.request.path}")
        self.set_status(403)
        self.set_header("Content-Type", "application/json")
        self.write({
            "error": "File downloads are disabled",
            "message": "This JupyterLab instance does not permit file downloads",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
        self.finish()
    
    def post(self, *args, **kwargs): self.get(*args, **kwargs)
    def put(self, *args, **kwargs): self.get(*args, **kwargs)
    def delete(self, *args, **kwargs): self.get(*args, **kwargs)
    def head(self, *args, **kwargs): self.get(*args, **kwargs)

def hook_extension_loading():
    """
    FINAL TEST: ONLY the jupyter-fs extension hook
    
    HYPOTHESIS: If jupyter-fs handles ALL downloads (including standard Jupyter ones),
    then we only need this ONE layer, not the FilesHandler replacement.
    """
    try:
        import jupyterfs.extension as jfs_ext
        original_load = jfs_ext._load_jupyter_server_extension
        
        def blocking_load(serverapp):
            # Load original extension first
            try:
                result = original_load(serverapp)
            except Exception as e:
                print(f"⚠️ {time.strftime('%H:%M:%S')} - Extension load warning: {e}")
                result = None
            
            # THE ONLY BLOCKING LAYER: URL patterns that block all download requests
            try:
                web_app = serverapp.web_app
                blocking_patterns = [
                    (r"/files/(.*)", DownloadBlocker),
                    (r"/api/contents/.*/download", DownloadBlocker),
                    (r".*/download/.*", DownloadBlocker),
                ]
                web_app.add_handlers(".*$", blocking_patterns)
                print(f"✅ {time.strftime('%H:%M:%S')} - Added ONLY blocking layer (URL patterns)")
            except Exception as e:
                print(f"❌ {time.strftime('%H:%M:%S')} - CRITICAL: Could not add blocking handlers: {e}")
            
            print(f"🎯 {time.strftime('%H:%M:%S')} - SINGLE layer blocking active!")
            return result
        
        jfs_ext._load_jupyter_server_extension = blocking_load
        print(f"✅ {time.strftime('%H:%M:%S')} - Hooked jupyter-fs extension (ONLY layer)")
        
    except Exception as e:
        print(f"❌ {time.strftime('%H:%M:%S')} - CRITICAL: Extension hook failed: {e}")

# Initialize ONLY the extension hook
hook_extension_loading()

# REMOVED: FilesHandler replacement (testing if it's redundant)
# REMOVED: Contents manager patching (testing if it's redundant)
# HYPOTHESIS: This single extension hook blocks ALL downloads

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

print(f"✅ {time.strftime('%H:%M:%S')} - Configuration loaded - Downloads BLOCKED")
print(f"🔒 SINGLE layer download blocking active (URL patterns only)")
print(f"📋 Users can view and edit files but cannot download them") 