FROM python:3.11.1 AS base

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE=1

ENV PROJECT_DIR /code
RUN mkdir ${PROJECT_DIR}
WORKDIR ${PROJECT_DIR}

RUN python3 -m pip install pipenv
ADD . ${PROJECT_DIR}/
#COPY Pipfile Pipfile.lock ${PROJECT_DIR}
RUN pipenv install --system --deploy
#ADD . ${PROJECT_DIR}/

CMD python manage.py migrate && python manage.py collectstatic --noinput && python manage.py test && python manage.py runserver 0.0.0.0:8000
#gunicorn --bind 0.0.0.0:$PORT --workers 3 --threads 8 --timeout 0 app.wsgi:application
#daphne -b 0.0.0.0 -p 8000 pison.asgi:application