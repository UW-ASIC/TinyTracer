ARG VARIANT=ubuntu-24.04
FROM mcr.microsoft.com/vscode/devcontainers/base:${VARIANT}

ENV DEBIAN_FRONTEND=noninteractive
ENV PDK_ROOT=/home/vscode/ttsetup/pdk
ENV PDK=ihp-sg13cmos5l
ARG TT_SUPPORT_TOOLS_BRANCH=ihp-sg13cmos5l

RUN apt update
RUN apt install -y iverilog gtkwave python3 python3-pip python3-venv python3-tk python-is-python3 libcairo2 verilator libpng-dev libqhull-dev

# Clone tt-support-tools
RUN mkdir -p /ttsetup
RUN git clone -b ${TT_SUPPORT_TOOLS_BRANCH} https://github.com/TinyTapeout/tt-support-tools /ttsetup/tt-support-tools

COPY test/requirements.txt /ttsetup/test_requirements.txt
COPY .devcontainer/copy_tt_support_tools.sh /ttsetup

RUN python -m venv /ttsetup/venv
RUN /ttsetup/venv/bin/pip install -r /ttsetup/test_requirements.txt -r /ttsetup/tt-support-tools/requirements.txt

# Install verible (for formatting)
RUN umask 022 && \
    curl -L https://github.com/chipsalliance/verible/releases/download/v0.0-4023-gc1271a00/verible-v0.0-4023-gc1271a00-linux-static-x86_64.tar.gz | \
    tar zxf - -C /usr/local --strip-components=1 && \
    chmod 755 /usr/local/bin

# Install LibreLane, the version tt-gds-action@ihp-cmos5l uses
RUN /ttsetup/venv/bin/pip install librelane==3.1.0.dev3

# Install the ihp-sg13cmos5l PDK. ciel cannot install it, so this follows
# tt-gds-action's install_sg13cmos5l.sh: the IHP-Open-PDK commit it pins.
ARG IHP_PDK_REV=2bbec755dc67ca3db0261c3d6163e15735d66710
RUN mkdir -p ${PDK_ROOT} && \
    git -C ${PDK_ROOT} init -q && \
    git -C ${PDK_ROOT} fetch -q --depth 1 https://github.com/IHP-GmbH/IHP-Open-PDK.git ${IHP_PDK_REV} && \
    git -C ${PDK_ROOT} checkout -q FETCH_HEAD && \
    echo "IHP-Open-PDK ${IHP_PDK_REV}" > ${PDK_ROOT}/ihp-sg13cmos5l/SOURCES
