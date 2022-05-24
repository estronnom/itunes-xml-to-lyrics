FROM python

WORKDIR /lyricsparser

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 8080

CMD python3 main.py
