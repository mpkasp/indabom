FROM python:3.11.1 as BASE

ENV APP_HOME /app
WORKDIR $APP_HOME

ARG SETTINGS_NAME

ENV SETTINGS_NAME=${SETTINGS_NAME}
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install pipenv
ADD . ${APP_HOME}/
RUN pipenv install --system --deploy

CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 indabom.wsgi:application