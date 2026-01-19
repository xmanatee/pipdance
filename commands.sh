#!/bin/bash
# pipdance commands - source this file: `source commands.sh`

PI=pi3@192.168.2.3
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

piper-sim() {
    cd "$DIR/src" && python -m piper.choreography \
        --poses ../scripts/poses.json \
        --he ../scripts/he.md --she ../scripts/she.md \
        --simulation --startup \
        --interpolation cubic --easing ease_out "$@"
}

piper-deploy() {
    scp -r "$DIR"/{src,setup,scripts} $PI:~/pipdance/
}

piper-run() {
    piper-deploy && ssh $PI 'cd ~/pipdance && source ~/piper-venv/bin/activate && \
        PYTHONPATH=src python -m piper.choreography \
        --poses scripts/poses.json --he scripts/he.md --she scripts/she.md \
        --adapter waveshare --startup --interpolation cubic --easing ease_out'
}

piper-dry() {
    cd "$DIR/src" && python -m piper.choreography \
        --poses ../scripts/poses.json \
        --he ../scripts/he.md --she ../scripts/she.md --dry-run
}

echo "pipdance commands loaded: piper-sim, piper-deploy, piper-run, piper-dry"
