import os
import sys

if not os.environ.get('SSH_PASSWORD'):
    print("Environment variable SSH_PASSWORD is not set. Exiting.", file=sys.stderr)
    sys.exit(1)
else:
    print("SSH_PASSWORD is set."+ os.environ.get('SSH_PASSWORD'))

if not os.environ.get('SSH_HOST'):
    print("Environment variable SSH_HOST is not set. Exiting.", file=sys.stderr)
    sys.exit(1)