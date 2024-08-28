FROM armdocker.rnd.ericsson.se/dockerhub-ericsson-remote/python:3.9.4-slim-buster

RUN apt-get clean

RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-server=1:7.9p1-10+deb10u4 && \
    apt-get install -y gcc=4:8.3.0-1

RUN pip install poetry

# A locale needs to be installed and set for later use by some python packages like click
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# Store all of the packages under the /usr/src/app/ directory
RUN mkdir -p /usr/src/app/
WORKDIR /usr/src/app
COPY poetry.lock pyproject.toml /usr/src/app/

# We turn off virtual env as not needed inside the container
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-interaction --no-ansi

EXPOSE 22

CMD ["/usr/sbin/sshd","-D"]
