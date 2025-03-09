FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy source code
COPY . .

# Define port
EXPOSE 5000

# Run the app
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000"]
