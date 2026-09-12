#FROM hn4930/telemac-debian:0.0.1
# 上方这个是通过原作者上传的镜像下载然后构建，下方是自主构建，基于DockerfileBase
FROM telemac-debian:0.1
LABEL maintainer="peter.steiner@flussplan.at"

ARG TELEMAC_MASCARET_VER=v8p4r0

ARG TELEMAC_ROOT=/opt/telemac-mascaret

ARG TELEMAC_TARGET="openmpi"

# RUN apt-get -o Dpkg::Options::="--force-confold" install -q -y git
COPY ./telemac-mascaret  ${TELEMAC_ROOT}/${TELEMAC_MASCARET_VER}
# COPY ./workdir ${TELEMAC_ROOT}/${TELEMAC_MASCARET_VER}/workdir
# RUN ${TELEMAC_ROOT}/checkout.sh

COPY *.sh ${TELEMAC_ROOT}/
RUN chmod +x ${TELEMAC_ROOT}/*.sh

COPY build.sh ${TELEMAC_ROOT}/
RUN chmod +x ${TELEMAC_ROOT}/build.sh
#
COPY systel.cfg ${TELEMAC_ROOT}
RUN ${TELEMAC_ROOT}/build.sh

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY setenv.sh /etc/profile.d/setenv.sh
RUN chmod +x /etc/profile.d/setenv.sh

# 额外的python环境
COPY setup-4-output.sh ${TELEMAC_ROOT}/
RUN chmod +x ${TELEMAC_ROOT}/setup-4-output.sh
#RUN apt-get update && apt-get install -y python3-pip python3-dev
RUN ${TELEMAC_ROOT}/setup-4-output.sh

# 在 .bashrc 和 .profile 中加载 /etc/profile.d/ 中的环境变量
RUN echo 'source /etc/profile.d/*.sh' >> /root/.bashrc && \
    echo 'source /etc/profile.d/*.sh' >> /root/.profile

# jdk相关
ADD ./dependencies/jdk-8u211-linux-x64.tar.gz /usr/local/
RUN ln -sv /usr/local/jdk1.8.0_211/ /usr/local/jdk \
    && echo "export JAVA_HOME=/usr/local/jdk" >> /etc/profile \
    && echo "export PATH=\$JAVA_HOME/bin:\$JAVA_HOME/jre/bin:\$PATH" >> /etc/profile \
    && echo "export CLASSPATH=.\$CLASSPATH:\$JAVA_HOME/lib:\$JAVA_HOME/jre/lib:\$JAVA_HOME/lib/tools.jar" >> /etc/profile

#时区
COPY ./dependencies/usr/share/zoneinfo/Asia/Shanghai /usr/share/zoneinfo/Asia/Shanghai
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' >/etc/timezone

ENV JAVA_HOME /usr/local/jdk
ENV JRE_HOME $JAVA_HOME/jre
ENV CLASSPATH $JAVA_HOME/lib/:$JRE_HOME/lib/
ENV PATH $PATH:$JAVA_HOME/bin


ENV TELEMAC_ROOT="${TELEMAC_ROOT}"
ENV TELEMAC_MASCARET_VER="${TELEMAC_MASCARET_VER}"
ENV TELEMAC_TARGET="${TELEMAC_TARGET}"

ENTRYPOINT [ "/entrypoint.sh"]