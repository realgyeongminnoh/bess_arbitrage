#!/bin/bash

# HISTORICAL / FORECASTED
IS_HISTORICAL_FLAG=true

if [ "$IS_HISTORICAL_FLAG" = true ]; then
    HISTORICAL_CLI_FLAG="--ih"
else
    HISTORICAL_CLI_FLAG=""
fi

# complete month range for system_marginal_prices you provided in data / inputs
python -u initialization.py $HISTORICAL_CLI_FLAG --cms 201501 --cme 202412


# ============================== FIXED PERFORMANCE PARAMETERS
# ============================== HISTORY

# 
# 
#


# ============================== MODEL PARAMETERS



# BATCH MONTH START & END
MONTH_START=202201
MONTH_END=202212

# ENERGY CAPACITY RATED
ENERGY_CAPACITY_RATED_START=10000
ENERGY_CAPACITY_RATED_INCREMENT=10000
ENERGY_CAPACITY_RATED_END=100000

# POWER OUTPUT RATED
POWER_OUTPUT_RATED_START=10000
POWER_OUTPUT_RATED_INCREMENT=10000
POWER_OUTPUT_RATED_END=100000

# FIXED PERFORMANCE PARAMETERS
STATE_OF_HEALTH=1
STATE_OF_CHARGE_INITIAL=0
STATE_OF_CHARGE_MINIMUM=0
STATE_OF_CHARGE_MAXIMUM=1
SELF_DISCHARGE_RATE=0
EFFICIENCY_CHARGE=1
EFFICIENCY_DISCHARGE=1
REST_BEFORE_CHARGE=0
REST_AFTER_DISCHARGE=0


# ============================== DO NOT MAKE CHANGE


CURRENT_YEAR=${MONTH_START:0:4}
CURRENT_MONTH=${MONTH_START:4:2}

echo "============================================================"
echo -n "MONTHS: "
echo "$MONTH_START, ..., $MONTH_END"

FIRST=$ENERGY_CAPACITY_RATED_START
LAST=$(( (ENERGY_CAPACITY_RATED_END - ENERGY_CAPACITY_RATED_START) / ENERGY_CAPACITY_RATED_INCREMENT * ENERGY_CAPACITY_RATED_INCREMENT + ENERGY_CAPACITY_RATED_START ))
echo "ENERGY CAPACITY RATED (kWh): $FIRST, ..., $LAST (Δ = +$ENERGY_CAPACITY_RATED_INCREMENT)"

FIRST=$POWER_OUTPUT_RATED_START
LAST=$(( (POWER_OUTPUT_RATED_END - POWER_OUTPUT_RATED_START) / POWER_OUTPUT_RATED_INCREMENT * POWER_OUTPUT_RATED_INCREMENT + POWER_OUTPUT_RATED_START ))
echo "POWER OUTPUT RATED (kW): $FIRST, ..., $LAST (Δ = +$POWER_OUTPUT_RATED_INCREMENT)"

echo -n "FIXED PERFORMANCE PARAMETERS: "
echo -n "$STATE_OF_HEALTH $STATE_OF_CHARGE_INITIAL $STATE_OF_CHARGE_MINIMUM $STATE_OF_CHARGE_MAXIMUM "
echo "$SELF_DISCHARGE_RATE $EFFICIENCY_CHARGE $EFFICIENCY_DISCHARGE $REST_BEFORE_CHARGE $REST_AFTER_DISCHARGE"
echo


while true; do
    MONTH=$(printf "%04d%02d" $CURRENT_YEAR $CURRENT_MONTH)

    if [ "$MONTH" -gt "$MONTH_END" ]; then
        break
    fi

    echo "$(date +'%Y-%m-%d %H:%M:%S') | $MONTH"

    # python -u parallel_monthly.py \
    #     $HISTORICAL_CLI_FLAG \
    #     --m "$MONTH" \
    #     --ecrs "$ENERGY_CAPACITY_RATED_START" \
    #     --ecri "$ENERGY_CAPACITY_RATED_INCREMENT" \
    #     --ecre "$ENERGY_CAPACITY_RATED_END" \
    #     --pors "$POWER_OUTPUT_RATED_START" \
    #     --pori "$POWER_OUTPUT_RATED_INCREMENT" \
    #     --pore "$POWER_OUTPUT_RATED_END" \
    #     --soh "$STATE_OF_HEALTH" \
    #     --socini "$STATE_OF_CHARGE_INITIAL" \
    #     --socmin "$STATE_OF_CHARGE_MINIMUM" \
    #     --socmax "$STATE_OF_CHARGE_MAXIMUM" \
    #     --sdr "$SELF_DISCHARGE_RATE" \
    #     --ec "$EFFICIENCY_CHARGE" \
    #     --ed "$EFFICIENCY_DISCHARGE" \
    #     --rbc "$REST_BEFORE_CHARGE" \
    #     --rad "$REST_AFTER_DISCHARGE" \
    #     > /dev/null 2>> errors.log

    if [ "$CURRENT_MONTH" -eq 12 ]; then
        CURRENT_MONTH=1
        CURRENT_YEAR=$((CURRENT_YEAR + 1))
    else
        CURRENT_MONTH=$((CURRENT_MONTH + 1))
    fi
done

echo "$(date +'%Y-%m-%d %H:%M:%S') | SIMULATION END"