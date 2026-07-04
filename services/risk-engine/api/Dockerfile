# Use a lightweight, official Python runtime as the base image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the dependency tracker first to leverage Docker caching layers
COPY requirements.txt .

# Install the exact Python packages required by the engine
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the API application source code and trained model weights
COPY . .

# Expose port 8000 to handle incoming sub-team network traffic
EXPOSE 8000

# Run the Uvicorn production server bound to all network interfaces
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]