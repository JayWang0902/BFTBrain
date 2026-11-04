# Optional machine-local overrides (JDK path, heap size); servers without this file keep the old defaults.
[ -f ../scripts/local_env.sh ] && source ../scripts/local_env.sh
java -Xmx${BFT_XMX:-55g} -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=dump.hprof --enable-preview -cp target/classes:target/dependency/* com.gbft.framework.coordination.$@
