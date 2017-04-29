FROM index.idevopscloud.com:5000/idevops_base/paas-controller-base:1.0
MAINTAINER idevopscloud/Jeff

ADD paas-controller.tar /ido/
ADD start.sh /
ADD python-kubernetes.tar /usr/local/lib/python2.7/dist-packages/
CMD [ "bash", "/start.sh" ]
