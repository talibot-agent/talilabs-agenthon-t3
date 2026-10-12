#!/usr/bin/env bash
# validate.sh IMAGE OUTCSV : run every public T3 unit, compare output parquet hashes with the
PLAT="--read-only --user 65534:65534 --cap-drop=ALL --security-opt no-new-privileges --tmpfs /tmp:rw,noexec,nosuid,nodev,size=64m --pids-limit 256 --ulimit nofile=1024:1024 --ulimit nproc=256:256 -e QFBENCH_SEED=0 -e QFBENCH_NETWORK=none"
# shipped reference, record container wall time (create->exit) like the dev harness.
IMG=$1; CSV=$2; U=/tmp/track3-simulation-public/units
echo "unit,status,n_events,container_sec,eps" > $CSV
for d in $U/*/; do n=$(basename $d); o=/tmp/val/$n; sudo rm -rf $o; mkdir -p $o; chmod 777 $o
  if [ -f $d/batch.json ]; then
    t0=$(date +%s.%N); sudo docker run --rm $PLAT --network none --cpus 4 --memory 16g --memory-swap 16g -v $d:/input:ro -v $o:/output $IMG simulate-batch --batch-dir /input/scenarios --out-dir /output >/dev/null 2>&1; rc=$?; t1=$(date +%s.%N)
    st=OK; ev=0; for r in $d/checks/reference_data/*/; do s=$(basename $r)
      for f in trace message_trace; do [ -f $r/$f.parquet ] && ! cmp -s $r/$f.parquet $o/$s/$f.parquet && st=MISMATCH; done
      ev=$((ev+$(python3 -c "import json;print(json.load(open('$r/events.json'))['n_events'])"))); done
  else
    t0=$(date +%s.%N); sudo docker run --rm $PLAT --network none --cpus 4 --memory 16g --memory-swap 16g -v $d:/input:ro -v $o:/output $IMG simulate --config /input/scenario.json --out /output/trace.parquet >/dev/null 2>&1; rc=$?; t1=$(date +%s.%N)
    st=OK; for f in trace message_trace; do [ -f $d/$f.parquet ] && ! cmp -s $d/$f.parquet $o/$f.parquet && st=MISMATCH; done
    ev=$(python3 -c "import json;print(json.load(open('$d/events.json'))['n_events'])")
  fi
  [ $rc -ne 0 ] && st=RC$rc
  python3 -c "t=$t1-$t0;print('$n,$st,$ev,%.3f,%.1f'%(t,$ev/t))" >> $CSV
done
