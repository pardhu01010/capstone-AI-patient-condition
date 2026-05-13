FROM python:3.10-slim

WORKDIR /app

# Install dependencies required for some Python packages and Prisma
RUN apt-get update && apt-get install -y gcc g++ curl && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy requirements and Prisma schema
COPY requirements.txt pyproject.toml ./
COPY schema.prisma ./

# Install python dependencies
RUN uv venv && \
    . .venv/bin/activate && \
    uv pip install -r requirements.txt

# Generate Prisma client
RUN . .venv/bin/activate && prisma generate

# Copy the rest of the application
COPY . .

EXPOSE 8000

# Run the app
CMD ["/bin/bash", "-c", ". .venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000"]
