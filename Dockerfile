FROM ubuntu:latest

LABEL org.opencontainers.image.authors="tigerblue77"

RUN apt-get update && \
    apt-get install -y ipmitool python3

# Assuming your Python functions are defined in functions.py
ADD functions.py /app/functions.py
ADD dell_idrac_fan_controller.py /app/dell_idrac_fan_controller.py

RUN chmod 0777 /app/*.py

WORKDIR /app

# HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 CMD [ "python3", "/app/healthcheck.py" ] # Make sure to create a healthcheck.py or adjust this line accordingly

CMD ["python3", "./dell_idrac_fan_controller.py"]
