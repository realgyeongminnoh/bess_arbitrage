import numpy as np


class Parameter:
    def __init__(
        self,
        ecr: float,
        por: float,
        soh: float,
        soc_ini: float,
        soc_min: float,
        soc_max: float,
        sdr: float,
        ec: float,
        ed: float,
        rbc: int,
        rad: int,
    ):
        # 
        self.ecr = ecr                  # energy capacity rated
        self.por = por                  # power output rated
        #
        self.soh = soh                  # state of health
        self.soc_ini = soc_ini          # state of charge initial
        self.soc_min = soc_min          # state of charge minimum
        self.soc_max = soc_max          # state of charge maximum
        #
        self.sdr = sdr                  # self discharge rate
        self.ec = ec                    # efficiency charge
        self.ed = ed                    # efficiency discharge
        self.rbc = rbc                  # rest before charge
        self.rad = rad                  # rest after discharge