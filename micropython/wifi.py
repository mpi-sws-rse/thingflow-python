import network

def wifi_connect(essid, password):
    # Connect to the wifi. Based on the example in the micropython
    # documentation.
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(essid, password)
        while not wlan.isconnected():
            pass
    print('network config: %s' % repr(wlan.ifconfig()))


def disable_wifi_ap():
    # Disable the built-in access point.
    wlan = network.WLAN(network.AP_IF)
    wlan.active(False)
    print('Disabled access point, network status is %s' %
          wlan.status())
