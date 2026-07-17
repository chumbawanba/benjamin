FROM python:3.12-slim
WORKDIR /srv
COPY pyproject.toml .
RUN pip install --no-cache-dir .[test]
COPY . .
RUN chown -R 1000:1000 /srv
USER 1000:1000
