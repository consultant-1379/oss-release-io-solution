FROM armdocker.rnd.ericsson.se/dockerhub-ericsson-remote/python:3.9.4-slim-buster

# Install packages
RUN apt-get update
RUN apt-get install curl -y
RUN apt-get install unzip -y

# Install kubectl
RUN curl -LO https://storage.googleapis.com/kubernetes-release/release/$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt)/bin/linux/amd64/kubectl
RUN chmod +x ./kubectl
RUN mv ./kubectl /usr/local/bin

# Install Helm
RUN curl -LO https://arm1s11-eiffel052.eiffel.gic.ericsson.se:8443/nexus/service/local/repositories/eo-3pp-foss/content/org/cncf/helm/3.2.0/helm-3.2.0.zip
RUN unzip helm-3.2.0.zip
RUN chmod +x ./linux-amd64/helm
RUN mv ./linux-amd64/helm /usr/local/bin/helm

# Install AWS CLI
RUN curl https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip
RUN unzip awscliv2.zip
RUN chmod +x ./aws
RUN ./aws/install

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
RUN poetry install --no-interaction --no-ansi --no-dev

# Copy the oris code into the image
COPY /oris /usr/src/app/oris/

# Run oris
ENTRYPOINT ["python", "-m", "oris"]

