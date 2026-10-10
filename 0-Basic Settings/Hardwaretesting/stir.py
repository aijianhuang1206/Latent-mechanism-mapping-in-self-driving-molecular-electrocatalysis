from ika.magnetic_stirrer import MagneticStirrer
import time
#port_plt = 'COM8'
#plate = MagneticStirrer(device_port=port_plt)


def stirring(plate=None, rate = 400, stirring_time=10):
    assert plate !=None, 'Please assign the magnetic stirrer'
    print(f'Stirring at {rate} rpm for {stirring_time} s')
    plate.start_stirring()
    plate.target_stir_rate = rate
    time.sleep(stirring_time)
    plate.stop_stirring()
    print('Finished stirring\n')
    time.sleep(1)

