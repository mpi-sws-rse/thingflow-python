import network
import utime

def wifi_connect(essid, password):
    # Connect to the wifi. Based on the example in the micropython
    # documentation.
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print('connecting to network ' + essid + '...')
        wlan.connect(essid, password)
        # connect() appears to be async - waiting for it to complete
        while not wlan.isconnected():
            print('waiting for connection...')
            utime.sleep(4)
            print('checking connection...')
        print('Wifi connect successful, network config: %s' % repr(wlan.ifconfig()))
    else:
        # Note that connection info is stored in non-volatile memory. If
        # you are connected to the wrong network, do an explicity disconnect()
        # and then reconnect.
        print('Wifi already connected, network config: %s' % repr(wlan.ifconfig()))


def disable_wifi_ap():
    # Disable the built-in access point.
    wlan = network.WLAN(network.AP_IF)
    wlan.active(False)
    print('Disabled access point, network status is %s' %
          wlan.status())
