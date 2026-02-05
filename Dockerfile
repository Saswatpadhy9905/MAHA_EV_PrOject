FROM node:20-slim

# Install Python and pip
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy all files
COPY . .

# Create Python virtual environment and install dependencies
RUN python3 -m venv /app/venv
RUN /app/venv/bin/pip install --upgrade pip
RUN /app/venv/bin/pip install -r requirements.txt

# Install Node.js dependencies
WORKDIR /app/server
RUN npm install

# Set environment variables
ENV NODE_ENV=production
ENV PYTHONPATH=/app
ENV PATH="/app/venv/bin:$PATH"

# Expose port
EXPOSE 3000

# Start the server
CMD ["node", "server.js"]
