'''Analog to Digital sensor (in ADC0) for the esp8266 microcontroller'''

# author:      Daniel Mizyrycki
# license:     MIT
# repository:  https://github.com/mzdaniel/micropython-iot

from machine import ADC

class ADCSensor:
    def __init__(self, sensor_id='', min_rd=0, max_rd=1024,
                 min_val=0, max_val=1):
        '''Initialize sensor

           min_rd and max_rd are used in sample for sensor calibration
           min_val and max_val are the sample limits
        '''
        self.sensor_id = sensor_id
        self.min_rd = min_rd
        self.max_rd = max_rd
        self.min_val = min_val
        self.max_val = max_val
        self.coef = (max_val - min_val) / (max_rd - min_rd)
        self.adc = ADC(0)

    def read(self) -> int:
        '''Get a sensor reading using Micropython API

           Return 0-1024 direct ADC (0~3.3v) reading
        '''
        return self.adc.read()

    def sample(self) -> float:
        '''Get an ADC interpolated reading using ThingFlow sensor API

           Return min_val~max_val
        '''
        reading = self.read()
        return self.min_val + (reading - self.min_rd) * self.coef
