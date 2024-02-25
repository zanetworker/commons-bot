FROM python:3.11-slim-bullseye

# Set the working directory in the container to /app
WORKDIR /app

RUN pip install --no-cache-dir poetry==1.6.1

# Copy only the pyproject.toml and optionally poetry.lock files to use Docker caching
COPY pyproject.toml poetry.lock* ./

# Set Poetry to not create a virtual environment and install dependencies
# Disabling virtualenv creation for Docker builds is a best practice
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi
    
# Copy the current directory contents into the container at /app
# This is done after installing dependencies to ensure that Docker's cache is used efficiently
COPY . .

EXPOSE 5002

CMD ["python", "commons-bot.py"]

# Set a non-root user and switch to it for security best practices
# Here 'user' should be replaced with the actual username you want to use.
# RUN adduser --disabled-password --gecos '' user
# USER user