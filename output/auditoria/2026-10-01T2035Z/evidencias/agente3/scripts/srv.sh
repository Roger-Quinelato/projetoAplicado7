#!/bin/bash
# Uso: srv.sh start <porta> <database_url> <log> [public]   |  srv.sh stop <porta>
SP=/tmp/claude-0/-home-user-projetoAplicado7/ec00d59b-c354-5d1f-b4d6-080b88ac1d06/scratchpad
A=$SP/agente3
cd $SP/iso
if [ "$1" = start ]; then
  EXTRA=()
  if [ "$5" = public ]; then EXTRA=(PUBLIC_DEMO=true DEMO_ACCESS_TOKEN="$(cat $A/.demo_token_local)"); fi
  env -u DATABASE_URL -u RABBITMQ_URL -u PUBLIC_DEMO -u DEMO_ACCESS_TOKEN DATABASE_URL="$3" ${RABBIT:+RABBITMQ_URL="$RABBIT"} "${EXTRA[@]}" PYTHONPATH=src \
    nohup $A/venv/bin/python -m uvicorn archcorp.main:app --host 127.0.0.1 --port "$2" ${WORKERS:+--workers $WORKERS} > "$4" 2>&1 &
  echo $! > $A/srv_$2.pid
  for i in $(seq 1 40); do curl -sf localhost:$2/health/live >/dev/null && { echo "srv $2 up (pid $(cat $A/srv_$2.pid))"; exit 0; }; sleep 0.5; done
  echo "srv $2 FAILED to start"; tail -5 "$4"; exit 1
elif [ "$1" = stop ]; then
  [ -f $A/srv_$2.pid ] && kill $(cat $A/srv_$2.pid) 2>/dev/null; sleep 1.5; rm -f $A/srv_$2.pid; echo "srv $2 stopped"
fi
