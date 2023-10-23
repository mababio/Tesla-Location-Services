FROM python:3.10-slim
ENV APP_HOME /app
ENV PORT 8080
#For folks who are not creating kubernetes secrets.
#ENV LAT_HOME <value>
#ENV LON_HOME <value>
#ENV HOME_RADIUS <value>
#ENV GMAPS_KEY <value>
#ENV HOME_STREET <value>
#ENV TESLA_USERNAME <value>
WORKDIR $APP_HOME
COPY src/* ./
RUN pip install --no-cache-dir -r  requirements.txt
RUN apt-get update && apt-get install vim curl lsof -y
CMD echo $CACHE_TESLA_JSON > cache.json; exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
