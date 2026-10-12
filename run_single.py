import os, sys, tempfile
# Platform runs --read-only --user 65534 with a 64 MiB tmpfs at /tmp. ABIDES' kernel creates
# ./log/<epoch> in the cwd, so resolve paths and move to a private dir on the tmpfs first.
argv = sys.argv[1:]
for i, a in enumerate(argv):
    if a in ("--config", "--out") and i + 1 < len(argv):
        argv[i + 1] = os.path.abspath(argv[i + 1])
os.chdir(tempfile.mkdtemp(prefix="t3run-"))
import t3lazy
t3lazy.install()
import t3fast
t3fast.apply()
from abides_fork.simulate import main
raise SystemExit(main(argv))
