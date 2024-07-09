FROM tsl0922/ttyd:latest

RUN apt update -y && apt upgrade -y
RUN apt install -y curl make net-tools unzip git openssh-client 

RUN apt install -y vim 
RUN apt install -y docker.io
RUN apt install -y jq
RUN apt-get clean


RUN curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
RUN chmod +x /usr/local/bin/docker-compose

CMD exec ttyd -p 7681 -c ati_support:ati112 -W -o -b /remote_terminal bash