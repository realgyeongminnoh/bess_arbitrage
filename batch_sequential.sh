#!/bin/bash

for year in {2015..2024}; do
    for month in {01..12}; do
        if [ "$month" -eq 12 ]; then
            next_month=01
            next_year=$((year + 1))
        else
            next_month=$(printf "%02d" $((10#$month + 1)))
            next_year=$year
        fi

        ds="${year}${month}01"
        de="${next_year}${next_month}01"

        for ecr in $(seq 1000 100 2000); do
            for por in $(seq 1000 100 2000); do
                if [ "$por" -gt "$ecr" ]; then
                    continue
                fi
                
                python -u main.py --ih \
                    --ds "$ds" \
                    --de "$de" \
                    --por "$por" \
                    --ecr "$ecr" \
                    > /dev/null
            done
        done
    done
done