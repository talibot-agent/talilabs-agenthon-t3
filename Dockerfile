# Tali Labs Track 3 submission: pinned baseline ABIDES stack + semantics-preserving speed layer.
# Base = the organizers' baseline image built from track3-simulation-public/baselines (tag t3base).
FROM t3base:latest
LABEL qfbench2.interface_version="2.0" \
      org.opencontainers.image.authors="Tali (AI agent) for team Tali Labs" \
      org.opencontainers.image.description="ABIDES T3 simulator with semantics-preserving speedups"
ENV HOME=/tmp TMPDIR=/tmp PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/opt PYTHONWARNINGS=ignore
COPY t3fast.py run_single.py run_batch.py /opt/
COPY simulate /usr/local/bin/simulate
COPY simulate-batch /usr/local/bin/simulate-batch
RUN chmod +x /usr/local/bin/simulate /usr/local/bin/simulate-batch \
 && python -m compileall -q /opt /usr/local/lib/python3.11 >/dev/null || true
WORKDIR /work
CMD ["simulate", "--help"]
