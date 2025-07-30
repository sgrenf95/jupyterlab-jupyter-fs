# Jupyter Server Configuration with Download Blocking
# Simple and effective approach to block ALL file downloads

import time
from tornado.web import HTTPError, RequestHandler
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

def apply_download_blocking():
    """Apply core download blocking mechanisms."""
    
    # Block core Jupyter file handlers
    try:
        import jupyter_server.services.contents.handlers as core_handlers
        core_handlers.FilesHandler = DownloadBlocker
        print(f"✅ {time.strftime('%H:%M:%S')} - Replaced FilesHandler")
    except Exception as e:
        print(f"⚠️ {time.strftime('%H:%M:%S')} - Could not patch handlers: {e}")
    
    # Block contents manager download methods
    try:
        import jupyter_server.services.contents.manager as contents_manager_module
        def blocked_download_url(self, path):
            print(f"🚫 {time.strftime('%H:%M:%S')} - Blocked download URL: {path}")
            raise HTTPError(403, "Downloads disabled")
        contents_manager_module.ContentsManager.get_download_url = blocked_download_url
        print(f"✅ {time.strftime('%H:%M:%S')} - Patched download methods")
    except Exception as e:
        print(f"⚠️ {time.strftime('%H:%M:%S')} - Could not patch contents manager: {e}")

def hook_extension_loading():
    """Hook into jupyter-fs extension to add download blocking."""
    try:
        import jupyterfs.extension as jfs_ext
        original_load = jfs_ext._load_jupyter_server_extension
        
        def blocking_load(serverapp):
            # Load original extension
            try:
                result = original_load(serverapp)
            except Exception as e:
                print(f"⚠️ {time.strftime('%H:%M:%S')} - Extension load warning: {e}")
                result = None
            
            # Add blocking handlers
            try:
                web_app = serverapp.web_app
                blocking_patterns = [
                    (r"/files/(.*)", DownloadBlocker),
                    (r"/api/contents/.*/download", DownloadBlocker),
                    (r".*/download/.*", DownloadBlocker),
                ]
                web_app.add_handlers(".*$", blocking_patterns)
                print(f"✅ {time.strftime('%H:%M:%S')} - Added blocking handlers")
            except Exception as e:
                print(f"⚠️ {time.strftime('%H:%M:%S')} - Could not add handlers: {e}")
            
            # Patch contents manager
            try:
                contents_manager = serverapp.contents_manager
                for method_name in ['getDownloadUrl', 'get_download_url']:
                    if hasattr(contents_manager, method_name):
                        def make_blocker():
                            def blocked(path):
                                raise HTTPError(403, "Downloads disabled")
                            return blocked
                        setattr(contents_manager, method_name, make_blocker())
                print(f"✅ {time.strftime('%H:%M:%S')} - Patched contents manager")
            except Exception as e:
                print(f"⚠️ {time.strftime('%H:%M:%S')} - Could not patch manager: {e}")
            
            print(f"🎉 {time.strftime('%H:%M:%S')} - Download blocking active!")
            return result
        
        jfs_ext._load_jupyter_server_extension = blocking_load
        print(f"✅ {time.strftime('%H:%M:%S')} - Hooked extension loading")
        
    except Exception as e:
        print(f"❌ {time.strftime('%H:%M:%S')} - Extension hook failed: {e}")

# Initialize download blocking
apply_download_blocking()
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

print(f"✅ {time.strftime('%H:%M:%S')} - Configuration loaded - Downloads BLOCKED")
print(f"🔒 Multi-layer download blocking active")
print(f"📋 Users can view and edit files but cannot download them") 