# Secure JupyterLab with Download Blocking
FROM condaforge/mambaforge:latest

WORKDIR /app

# Install packages
COPY environment.yml .
RUN mamba env update -n base -f environment.yml && mamba clean -afy

# Install system dependencies
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y sudo curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Create user with extension management privileges
RUN useradd -m -s /bin/bash jovyan && \
    chown -R jovyan:jovyan /app && \
    usermod -aG sudo jovyan && \
    echo "jovyan ALL=(ALL) NOPASSWD: /opt/conda/bin/jupyter" >> /etc/sudoers

# Create directories
RUN mkdir -p /home/jovyan/.jupyter/labconfig && \
    mkdir -p /opt/conda/share/jupyter/labextensions && \
    chown -R jovyan:jovyan /home/jovyan && \
    chown -R jovyan:jovyan /opt/conda/share/jupyter && \
    chmod -R 755 /opt/conda/share/jupyter

# Copy configuration files
COPY jupyter_server_config.py /home/jovyan/.jupyter/

# Set file permissions
RUN chown -R jovyan:jovyan /home/jovyan/.jupyter

# Switch to non-root user
USER jovyan

# Environment variables
ENV JUPYTER_ENABLE_LAB=yes \
    JUPYTER_TOKEN="" \
    JUPYTER_PASSWORD="" \
    JUPYTER_ALLOW_INSECURE_WRITES=1 \
    JUPYTER_DISABLE_DOWNLOADS=1

# Security headers
ENV JUPYTER_CSP_ENABLED=1 \
    PYTHONHTTPSVERIFY=1

EXPOSE 8888

# Start JupyterLab with download blocking
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--ServerApp.token=", "--ServerApp.password="] 