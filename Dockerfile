FROM python:3.11-slim

# Set environment variables
ENV DB_PATH=/app/data/styleseat.db
ENV TELEGRAM_BOT_TOKEN="6453639963:AAG7QR5MH8PEYkxvlIxCN_5tTR1MRHNyUFo"

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create a directory for the SQLite database file
#RUN mkdir /data
#RUN mv /app/reservations.db /app/data/

# Run the bot
#CMD ["python3", "master.py"]
CMD ["python3", "style.py"]