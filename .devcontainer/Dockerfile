FROM mcr.microsoft.com/devcontainers/python:3.13

# System libs for WeasyPrint (PDF)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    libcairo2 libpango-1.0-0 libpangoft2-1.0-0 pango1.0-tools \
    libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
