#!/usr/bin/env bash
set -euo pipefail

GIT_ROOT=$(git rev-parse --show-toplevel)

CIRCUIT_PATH=$GIT_ROOT/tests/$1
if [[ ! -d $CIRCUIT_PATH ]]; then
   echo "Path $CIRCUIT_PATH does not exist"
   exit 1
fi

source /etc/profile.d/modules.sh

module purge
module load unstable snakemake

BUILD_DIR=$CIRCUIT_PATH/build

if [[ -d $BUILD_DIR ]]; then
  rm -r $BUILD_DIR
fi

mkdir $BUILD_DIR
pushd $BUILD_DIR

# Unset SLURM environment variables
unset $(env | grep SLURM | cut -d= -f1 | xargs)

snakemake -p -j8                                \
  --snakefile "$GIT_ROOT/snakemake/Snakefile"   \
  --config "bioname=$CIRCUIT_PATH"              \
  --cluster-config "$CIRCUIT_PATH/cluster.yaml" \
  --                                            \
  functional_all functional_sonata

popd
