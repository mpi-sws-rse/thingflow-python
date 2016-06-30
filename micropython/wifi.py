
def wifi_connect(essid, password):
    # Connect to the wifi. Based on the example in the micropython
    # documentation.
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network...')
        wlan.connect(essid, password)
        while not wlan.isconnected():
            pass
    print('network config: %s' % repr(wlan.ifconfig()))
