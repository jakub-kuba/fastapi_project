# use official python image as a base
FROM python:3.9-slim

# set working directory in the container
WORKDIR /app

# copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy all the files to container
COPY . .

# set environment variable for unbuffered output in Python (helps with logging)
ENV PYTHONUNBUFFERED 1

# oper port 8000
EXPOSE 8000

# set default command to run the app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
