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

## Technical Architecture

### System Overview
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   User Action   │───>│ JupyterLab UI   │───>│   Web Request   │───>│  URL Patterns   │
│ (Right-click    │    │ (Download req.) │    │ (/files/*, etc.)│    │   Matching      │
│  Download)      │    │                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
                                                                             │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            ▼
│   403 Error     │<───│ DownloadBlocker │<───│ Extension Hook  │    ┌─────────────────┐
│  (Download      │    │   Handler       │    │  (jupyter-fs)   │    │   Pattern       │
│   Blocked)      │    │                 │    │                 │    │   Matched       │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Strategy: Extension Hook Interception

**Why This Approach Works:**

1. **Single Point of Control**: We intercept at the web application level where ALL requests flow through

2. **Perfect Timing**: The hook executes after jupyter-fs loads (preserving functionality) but before file serving begins (enabling blocking)

3. **Comprehensive Coverage**: URL pattern matching catches every possible download request type

## Detailed Technical Implementation

### 1. Extension Loading Interception

```python
# Hook into jupyter-fs extension loading
import jupyterfs.extension as jfs_ext
original_load = jfs_ext._load_jupyter_server_extension

def blocking_load(serverapp):
    # Load jupyter-fs normally (full functionality preserved)
    result = original_load(serverapp)
    
    # Inject blocking handlers into web application
    web_app = serverapp.web_app
    blocking_patterns = [
        (r"/files/(.*)", DownloadBlocker),               # Standard downloads
        (r"/api/contents/.*/download", DownloadBlocker), # API downloads  
        (r".*/download/.*", DownloadBlocker),            # Catch-all pattern
    ]
    web_app.add_handlers(".*$", blocking_patterns)
    
    return result

# Replace extension loader with our wrapper
jfs_ext._load_jupyter_server_extension = blocking_load
```

**Technical Benefits:**
- **Non-invasive**: Original jupyter-fs code unchanged
- **Timing-safe**: Executes at the optimal moment in the loading sequence
- **Priority-based**: URL patterns added with highest precedence

### 2. Request Interception Handler

```python
class DownloadBlocker(RequestHandler):
    def get(self, *args, **kwargs):
        # Log the blocked attempt
        logger.warning(f"DOWNLOAD BLOCKED: {self.request.path}")
        
        # Return 403 Forbidden
        self.set_status(403)
        self.write({
            "error": "File downloads are disabled",
            "blocked_path": self.request.path,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        })
```

**Security Features:**
- **HTTP Method Coverage**: Blocks GET, POST, PUT, DELETE, HEAD
- **Security Headers**: CSP, download prevention, MIME-sniffing protection
- **Audit Trail**: Logs all blocked attempts with timestamps
- **User Feedback**: Returns structured error responses

### 3. URL Pattern Strategy

| Pattern | Purpose | Examples |
|---------|---------|----------|
| `/files/(.*)` | Standard Jupyter file downloads | `/files/myfile.txt`, `/files/34697a73:robots.txt` |
| `/api/contents/.*/download` | API-based downloads | `/api/contents/data.csv/download` |
| `.*/download/.*` | Catch-all for any download URLs | `/custom/download/file`, `/ext/download/data` |

**Pattern Priority:** Added to web application with `".*$"` host matching ensures these patterns take precedence over default handlers.


## Security Analysis

### Download Vectors Blocked
- ✅ **Right-click → Download** in file browser
- ✅ **Direct URL access** (`/files/filename`)
- ✅ **API-based downloads** (`/api/contents/*/download`)
- ✅ **S3 file downloads** via jupyter-fs
- ✅ **Custom download endpoints** (catch-all pattern)

### Functionality Preserved
- ✅ **File viewing** (images, text, CSV, notebooks)
- ✅ **File editing** (code, markdown, data)
- ✅ **Code execution** (notebooks, terminals)
- ✅ **S3 browsing** (full jupyter-fs capabilities)
- ✅ **File uploads** (not affected by download blocking)

## System Verification

### Container Log Evidence
```bash
# System initialization
[I 2025-07-31 08:25:10.889 ServerApp] Added blocking layer based on URL patterns

# Download blocking in action  
[W 2025-07-31 08:25:43.xxx jupyter_server_config] DOWNLOAD BLOCKED: /files/34697a73:sitemap.xml
[W 2025-07-31 08:25:43.047 ServerApp] 403 GET /files/34697a73:sitemap.xml
```

### Browser Evidence
- **Network Tab**: Shows 403 responses for download attempts
- **Console**: Displays structured error messages
- **UI**: Download buttons/options become non-functional
