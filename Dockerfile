FROM python:3.9
LABEL maintainer="Urban Institute"

ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /requirements.txt
COPY ./app /app
COPY ./scripts /scripts

WORKDIR /app

RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /requirements.txt && \
    adduser --disabled-password --no-create-home urban && \
    # folder to serve static files by nginx
    mkdir -p /vol/web/static && \
    # folder to serve media files by nginx
    mkdir -p /vol/web/media && \
    chown -R urban:urban /vol && \
    chmod -R 755 /vol/web && \
    chmod -R +x /scripts

ENV PATH="/scripts:/py/bin:$PATH"

USER urban

CMD ["run.sh"]