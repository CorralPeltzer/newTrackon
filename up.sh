#!/bin/sh
PYTHONPATH=.:..
export PYTHONPATH
for t in tpl/static/*.mako;
do
    s=`echo "$t"|sed 's,tpl/,,; s/mako$/html/'`
    echo ./aux/mako-render $t '>' $s
    ./contrib/mako-render $t > $s
done

appcfg.py update .
