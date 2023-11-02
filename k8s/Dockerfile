FROM python:3.10-slim
RUN apt-get update && apt-get install vim curl lsof -y
######create appuser and directory for app#########
RUN groupadd -g 999 appuser && \
    useradd -m -r -u 999 -g appuser appuser
USER appuser
ENV APP_HOME  /home/appuser/app
RUN mkdir /home/appuser/app
RUN chown appuser:appuser /home/appuser/app
###### Create appuser and directory for application#########


WORKDIR $APP_HOME
COPY src/* ./



###### Create Python Virutal evironment ###########
RUN python -m venv $APP_HOME
RUN . $APP_HOME/bin/activate && pip install -r requirements.txt
# make sure all messages always reach console
ENV PYTHONUNBUFFERED=1
###### Create Python Virutal evironment ###########


####### Application specfic varaibles ##########
ENV PORT 8080
#################### For folks who are not creating kubernetes secrets ####################
#ENV LAT_HOME <value>
#ENV LON_HOME <value>
#ENV HOME_RADIUS <value>
#ENV GMAPS_KEY <value>
#ENV HOME_STREET <value>
#ENV TESLA_USERNAME <value>
#ENV CACHE_TESLA_JSON <VALUE>
#ENV GEOAPIFY_KEY <VALUE>
#ENV GEOAPIFY_URL <VALUE>
#################### For folks who are not creating kubernetes secrets ####################
####### Application specfic varaibles ##########

CMD echo $CACHE_TESLA_JSON > cache.json; . $APP_HOME/bin/activate && exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
