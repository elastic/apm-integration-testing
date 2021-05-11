FROM ubuntu:20.04

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive \
     TZ=UTC \
      apt-get install --no-install-recommends --no-install-suggests -y \
        build-essential autoconf libtool pkg-config ca-certificates \
        cmake gcc g++ python3 git nginx libpcre3-dev

RUN git clone --shallow-submodules --depth 1 --recurse-submodules -b v1.35.0 https://github.com/grpc/grpc \
  && cd grpc \
  && mkdir -p cmake/build \
  && cd cmake/build \
  && cmake -DgRPC_INSTALL=ON -DgRPC_BUILD_TESTS=OFF -DgRPC_BUILD_CSHARP_EXTENSIONS=OFF ../.. \
  && make -j2 \
  && make install

RUN git clone --shallow-submodules --depth 1 -b "v0.4.0" --recurse-submodules \
  https://github.com/open-telemetry/opentelemetry-cpp.git \
  && cd opentelemetry-cpp \
  && mkdir build \
  && cd build \
  && cmake -DWITH_OTLP=ON -DBUILD_TESTING=OFF -DWITH_EXAMPLES=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON .. \
  && make -j2 \
  && make install

RUN git clone --depth 1 -b "v0.1.0" https://github.com/open-telemetry/opentelemetry-cpp-contrib.git \
  && mkdir -p opentelemetry-cpp-contrib/instrumentation/nginx/build \
  && cd opentelemetry-cpp-contrib/instrumentation/nginx/build \
  && cmake -DCMAKE_INSTALL_PREFIX=/usr/share/nginx/modules .. \
  && make \
  && make install

COPY otel.toml /etc/otel.toml
COPY nginx.conf /etc/nginx/nginx.conf

CMD ["/usr/sbin/nginx", "-g", "daemon off;"]
EXPOSE 80
