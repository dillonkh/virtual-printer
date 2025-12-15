FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    ghostscript \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN cd /tmp \
    && wget https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs10060/ghostpdl-10.06.0.tar.gz \
    && tar -xzf ghostpdl-10.06.0.tar.gz \
    && cd ghostpdl-10.06.0 \
    && ./configure \
    && make pcl \
    && make install \
    && cd /tmp \
    && rm -rf ghostpdl-10.06.0 ghostpdl-10.06.0.tar.gz \
    && apt-get purge -y wget build-essential \
    && apt-get autoremove -y

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/outputs

EXPOSE 9100 8000

CMD ["python", "socket_server.py"]
