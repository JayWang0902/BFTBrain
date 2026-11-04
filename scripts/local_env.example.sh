# Local (macOS) environment for running BFTBrain on one machine.
# Copy to scripts/local_env.sh and adjust paths. local_env.sh itself is not committed.
export JAVA_HOME="$HOME/bft-tools/jdk-20.0.2+9/Contents/Home"
export PATH="$HOME/BFTBrain/.venv/bin:$JAVA_HOME/bin:$PATH"
export BFT_XMX=4g
export MAVEN_OPTS="-Dmaven.repo.local=$HOME/BFTBrain/.m2"
