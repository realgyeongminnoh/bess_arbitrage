#!/bin/bash

# Global toggles (comment/uncomment to control behavior)
# IS_MINUTE="--is_minute"
IS_HISTORICAL="--is_historical"
END_EXCLUDE="--end_exclude"
PARAMETER_PNNL="--parameter_pnnl"

# Fixed PNNL arguments
PNNL_YEAR=2023
# PNNL_TECHNOLOGY="Lithium-ion_LFP"
# PNNL_TECHNOLOGY="Lithium-ion_NMC"
PNNL_TECHNOLOGY="Vanadium_Redox_Flow"
# PNNL_TECHNOLOGY="Lead_Acid"
PNNL_ESTIMATE="Low"
PNNL_FXRATE=1333

# Loop through months in 2022, from Jan to Dec
for MONTH in $(seq -w 1 12); do
  # Format time_start and time_end
  TIME_START="2022${MONTH}0100"
  
  # Compute next month
  if [ "$MONTH" -eq 12 ]; then
    TIME_END="2023010100"
  else
    NEXT_MONTH=$(printf "%02d" $((10#$MONTH + 1)))
    TIME_END="2022${NEXT_MONTH}0100"
  fi

  # Run all 3 solver models
  for SOLVER_MODEL in 0 1 2; do

    echo $TIME_START $TIME_END

    python -u main.py \
      $IS_MINUTE \
      $IS_HISTORICAL \
      $END_EXCLUDE \
      $PARAMETER_PNNL \
      --time_start $TIME_START \
      --time_end $TIME_END \
      --pnnl_year $PNNL_YEAR \
      --pnnl_technology $PNNL_TECHNOLOGY \
      --pnnl_estimate $PNNL_ESTIMATE \
      --pnnl_fxrate $PNNL_FXRATE \
      --solver_model $SOLVER_MODEL
  done
done