# Use an official Python runtime as a parent image
FROM python:3.8.13-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the content of the local src directory to the working directory
COPY . .

# Make port 5002 available to the world outside this container
EXPOSE 5002

# Command to run the app
CMD ["python", "app_http_mode.py"]
# CMD ["python", "app.py"]
