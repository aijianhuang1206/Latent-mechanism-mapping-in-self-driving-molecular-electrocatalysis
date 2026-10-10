import MXII_valve as mxii
#valve_address = MXII_valve.find_address()[0]
#valve_switch = mxii.MX_valve('COM7', ports=2, name='Switching', verbose=True)
#valve_select = mxii.MX_valve('COM4', ports=6, name='Selection', verbose=True)
#valve_switch.get_port()
#valve_switch.change_port(1)# need to open the software and make sure it is on BCD level
#valve_select.get_port()
#valve_select.change_port(4)


def changing_port(valve=None, target_port=1):
    valve.change_port(target_port)
