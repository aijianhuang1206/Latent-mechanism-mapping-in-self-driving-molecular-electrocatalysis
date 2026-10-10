from alicat import FlowController
#flow_controller = FlowController(port='COM5')
#print(flow_controller.get())
#flow_controller.set_gas('N2')

def control_MFC(flow_controller=None, operation='open'):
    """
    :param flow_controller: FlowController
    :param operation: str, open or close
    :return:
    """
    if operation=='open':
        flow_controller.set_flow_rate(20)
        #flow_controller._set_control_point()
    elif operation=='close':
        flow_controller.set_flow_rate(0)
    elif operation=='inject':
        flow_controller.set_pressure(160)
    else:
        raise AssertionError('Please provide valid command to MFC.')
