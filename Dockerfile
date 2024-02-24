# Use an official Python runtime as a parent image
FROM python:3.11-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry

# Copy the pyproject.toml and optionally poetry.lock file to the working directory
COPY pyproject.toml poetry.lock* ./

# Install dependencies using Poetry in a way that doesn't create a virtual environment
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*
# Verify the SQLite version
RUN sqlite3 --version

# Copy the content of the local src directory to the working directory
COPY . .

# Make port 5002 available to the world outside this container
EXPOSE 5002

# Command to run the app
CMD ["python", "commons-bot.py"]
# CMD ["python", "app.py"]
