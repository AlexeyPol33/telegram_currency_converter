FROM python:3.10.11

WORKDIR /harvester

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . /harvester/

CMD python database/model.py create_tables && \
    python harvester/imoex_harvester.py start

