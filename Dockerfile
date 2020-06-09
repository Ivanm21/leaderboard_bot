# Use the official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8-slim

# Copy local code to the container image.
RUN mkdir -p /usr/src/app
ENV APP_HOME /usr/src/app

WORKDIR ${APP_HOME}
COPY requirements.txt ./

RUN python3 -m pip install -r requirements.txt

COPY . ./

# Install production dependencies.

CMD ["python", "./main.py"]
