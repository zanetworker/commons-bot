# Builder stage
FROM python:3.11-slim-bullseye as builder

WORKDIR /app

# Install poetry in the build stage
RUN pip install --no-cache-dir poetry==1.6.1

# Copy the pyproject.toml and poetry.lock files to install dependencies
COPY pyproject.toml poetry.lock* ./

# Install dependencies without creating a virtual environment
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy the source code
COPY . .


# Final stage
FROM python:3.11-slim-bullseye

WORKDIR /app

# Copy the installed packages from the builder stage
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

EXPOSE 10000

CMD ["python", "commons-bot.py"]

# Uncomment the following lines to set a non-root user, replacing 'user' with your chosen username
# RUN adduser --disabled-password --gecos '' user
# USER user
