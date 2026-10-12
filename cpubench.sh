#!/usr/bin/env bash
# cpubench.sh : interleaved CPU-time (user+sys of the whole container process tree) benchmark,
# robust to the shared box's load. Prints unit,image,rep,cpu_sec
U=/tmp/track3-simulation-public/units
for u in t3-s001-price-time-priority t3-ca-thin-book-depth t3-as06-throughput-fast t3-mr-cancel-replace-churn t3-mr-checkpoint-cadence-fine t3-coarse-tick-ties; do
 for rep in 1 2; do for img in t3base:latest talit3:v1 talit3:v2; do o=/tmp/cb; sudo rm -rf $o; mkdir -p $o
  c=$(sudo docker run --rm --network none --cpus 4 -v $U/$u:/input:ro -v $o:/output $img bash -c 'simulate --config /input/scenario.json --out /output/trace.parquet >/dev/null 2>&1; times' | tail -1 | python3 -c "
import sys,re;v=re.findall(r'(\d+)m([\d.]+)s',sys.stdin.read());print(round(sum(int(a)*60+float(b) for a,b in v),2))")
  echo "$u,$img,$rep,$c"; done; done; done
