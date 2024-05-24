#! /usr/bin/bash

URL_LIST=$1

BROWSER=curl
STOP=./stop
NETDEV=eth0

DELAY=3s

TO_KILL=

if [[ ! -f "$STOP" ]]; then
    printf "Error: File \"$STOP\" does not exist!\n"
    exit 1
fi

cat $URL_LIST | while read LINE || [[ -n $LINE ]];
do
    echo Creating suspended "$BROWSER" on "$LINE"
    $STOP $BROWSER $LINE &
    PID=$!
    TO_KILL="$PID $TO_KILL"
    echo Process: $PID

    # Wait for the process to stop
    while true;
    do
      status=$(top -p $PID -b -n 1 | tail -n 1)
      stopped=$(grep "T" /proc/$PID/status)
      [[ ! $stopped ]] || break;
    done
    echo Process $PID is stopped.

    # Launch measurement/packet loss commands
    netstat -taucp |& grep "$PID" &
    TO_KILL="$! $TO_KILL"

    strace -p $PID |& grep "SOCK_" &
    TO_KILL="$1 $TO_KILL"

    tc qdisc add dev $NETDEV root netem loss 0.1%

    # Restart the process
    kill -18 $PID

    # Give the browser some time to connect
    sleep $DELAY

    # Kill all outstanding processes
    echo Killing all outstanding processes...
    echo TO_KILL="$TO_KILL"
    for to_kill in $TO_KILL
    do
        echo Killing PID=$to_kill
        kill -9 $to_kill > /dev/null 2> /dev/null
    done

    echo Restoring Network State...
    tc qdisc del dev $NETDEV root

    echo Done.

done
