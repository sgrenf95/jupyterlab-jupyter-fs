# Secure JupyterLab with Download Blocking

A Docker setup providing JupyterLab with jupyter-fs for S3 file browsing while completely blocking all file downloads for security.

## 🔒 Security Features

- **JupyterLab 4.4** with modern interface
- **jupyter-fs** for S3 and filesystem browsing
- **Complete download blocking** - view and edit files but cannot download

## 🚀 Quick Start

```bash
# Build container
docker build -t secure-jupyterlab .

# Run with AWS credentials
docker run -d --name secure-jupyterlab -p 8888:8888 -v "C:/Users/elian/.aws:/home/jovyan/.aws:ro" -e AWS_DEFAULT_REGION=eu-west-1 secure-jupyterlab

# Access JupyterLab
open http://localhost:8888
```

## ☁️ S3 Configuration

Configure S3 via JupyterLab Settings:

1. Go to **Settings → Advanced Settings Editor → jupyter-fs**
2. Add your configuration:

```json
{
  "resources": [
    {
      "name": "My S3 Bucket",
      "url": "s3://<my-bucket>",
      "type": "fsspec",
      "defaultWritable": true,
      "auth": "none"
    }
  ]
}
```

**Important**: Use `"type": "fsspec"` for S3 (not `"pyfs"`).

## 🔒 What's Blocked vs. What Works

### ✅ **ENABLED:**
- Browse files and folders
- View file contents (text, images, CSV, notebooks)
- Edit files and notebooks
- Run code and execute notebooks
- Create new files
- S3 file system integration

### 🚫 **BLOCKED:**
- Download files to local machine
- Right-click download options
- "Save As" to local filesystem


---

# 🔒 Download Blocking Implementation

## How It Works

The download blocking system uses a **single, minimal layer** that intercepts all download requests at the web application level. After extensive testing, we discovered that only one mechanism is needed to block ALL downloads.

## Architecture

```
User Download Request → jupyter-fs Extension Hook → URL Pattern Matching → DownloadBlocker → 403 Error
```

## Implementation Details

### Single Blocking Layer

**Location**: `jupyter_server_config.py` → `hook_extension_loading()`

The system hooks into the jupyter-fs extension loading process and adds URL pattern handlers that catch all download requests:

```python
def hook_extension_loading():
    import jupyterfs.extension as jfs_ext
    original_load = jfs_ext._load_jupyter_server_extension
    
    def blocking_load(serverapp):
        # Load original jupyter-fs extension first
        result = original_load(serverapp)
        
        # Add URL patterns that block ALL download requests
        web_app = serverapp.web_app
        blocking_patterns = [
            (r"/files/(.*)", DownloadBlocker),           # Standard Jupyter downloads
            (r"/api/contents/.*/download", DownloadBlocker), # API downloads
            (r".*/download/.*", DownloadBlocker),        # Any download URLs
        ]
        web_app.add_handlers(".*$", blocking_patterns)
        
        return result
    
    # Replace the extension loading function
    jfs_ext._load_jupyter_server_extension = blocking_load
```

### DownloadBlocker Handler

The `DownloadBlocker` class returns 403 errors for all download attempts:

```python
class DownloadBlocker(RequestHandler):
    def prepare(self):
        # Security headers
        self.set_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; object-src 'none';")
        self.set_header('X-Download-Options', 'noopen')
        self.set_header('X-Content-Type-Options', 'nosniff')
    
    def get(self, *args, **kwargs):
        print(f"🚫 {time.strftime('%H:%M:%S')} - BLOCKED: {self.request.path}")
        self.set_status(403)
        self.write({
            "error": "File downloads are disabled",
            "message": "This JupyterLab instance does not permit file downloads",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
```

## Why This Single Layer Works

1. **Perfect Timing**: Applied after jupyter-fs loads, so it overrides all download mechanisms
2. **Comprehensive URL Coverage**: Pattern matching catches all possible download requests
3. **Web App Level**: Intercepts requests before they reach any file handlers
4. **Universal Blocking**: Works for both standard Jupyter and jupyter-fs downloads

## Verification

### Container Logs

Successful blocking appears in logs as:
```bash
🚫 16:19:10 - BLOCKED: /files/34697a73%3Arobots.txt
🎯 16:19:08 - SINGLE layer blocking active!
```

### Blocked Download Types

✅ **All these download methods are blocked**:
- Right-click → Download in file browser
- Direct URL access to `/files/*`
- API calls to `/api/contents/*/download`
- Any URL containing `/download/`
- Both standard Jupyter and S3 files via jupyter-fs

## Troubleshooting

**Downloads still work?**
- Check logs for `🎯 SINGLE layer blocking active!`
- Verify jupyter-fs extension is loaded
- Rebuild Docker image if config changes made

**No blocking logs?**
- Ensure `jupyter_server_config.py` is in `/home/jovyan/.jupyter/`
- Check for error messages during container startup

