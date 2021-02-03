import machine
import network
import time
import settings
import socket
import sys

try:
    import uasyncio as asyncio
except ImportError:
    import asyncio

import trickLED
from trickLED import animations
from trickLED import generators
from trickLED.testing import timeit


def connect(ssid, password, timeout=30):
    """  Connect to WiFi network  """
    timeout_tm = time.time() + timeout
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    sta.connect(ssid, password)
    while not sta.isconnected():
        if time.time() > timeout_tm:
            print('Could not connect to network')
            return sta
    ip = sta.ifconfig()[0]
    print('Connected to %s on %s' % (ssid, ip))
    return sta


def play(animation, n_frames, **kwargs):
    try:
        asyncio.run(animation.play(n_frames, **kwargs))
    except KeyboardInterrupt as e:
        animation._print_fps()
        raise e
    finally:
        # needed to reset state otherwise the animations will get all jumbled when ended with CTRL+C
        asyncio.new_event_loop()
        animation.leds.fill(0)
        animation.leds.write()
        time.sleep(1)


def demo_animations(leds, n_frames=200):
    print('Demonstrating animations press CTRL+C to cancel... or wait about 2 minutes.')
    # store repeat_n so we can set it back if we change it
    leds_repeat_n = leds.repeat_n
    # LitBits
    ani = animations.LitBits(leds)
    print('LitBits settings: default')
    play(ani, n_frames)
    print('LitBits settings: lit_percent=50')
    play(ani, n_frames, lit_percent=50)
    
    # NextGen
    ani = animations.NextGen(leds)
    print('NextGen settings: default')
    play(ani, n_frames)
    print('NextGen settings: blanks=2, interval=150')
    play(ani, n_frames, blanks=2, interval=150)
    
    # Jitter
    ani = animations.Jitter(leds)
    print('Jitter settings: default')
    play(ani, n_frames)
    print('Jitter settings: background=0x020212, fill_mode=FILL_MODE_SOLID')
    ani.generator = generators.random_vivid()
    play(ani, n_frames, background=0x020212, fill_mode=trickLED.FILL_MODE_SOLID)
    
    # SideSwipe
    ani = animations.SideSwipe(leds)
    print('SideSwipe settings: default')
    play(ani, n_frames)
    
    if leds.n > 60:
        print('Setting leds.repeat_n = 40, set it back to {} if you cancel the demo'.format(leds_repeat_n))
        leds.repeat_n = 40
    
    # Fire
    ani = animations.Fire(leds)
    print('Fire settings: default')
    play(ani, n_frames)
    
    # Divergent
    ani = animations.Divergent(leds)
    print('Divergent settings: default')
    play(ani, n_frames)
    print('Divergent settings: fill_mode=FILL_MODE_MULTI')
    play(ani, n_frames, fill_mode=trickLED.FILL_MODE_MULTI)
    
    # Convergent
    ani = animations.Convergent(leds)
    print('Convergent settings: default')
    play(ani, n_frames)
    print('Convergent settings: fill_mode=FILL_MODE_MULTI')
    play(ani, n_frames, fill_mode=trickLED.FILL_MODE_MULTI)

    # Conjuction
    ani = animations.Conjunction(leds)
    print('Conjuction settings: default')
    play(ani, n_frames)
    
    if leds.repeat_n != leds_repeat_n:
        leds.repeat_n = leds_repeat_n


def demo_generators(leds, n_frames=200):
    print('Demonstrating generators:')
    # stepped_color_wheel  
    print('stepped_color_wheel')
    ani = animations.NextGen(leds, generator = generators.stepped_color_wheel())
    play(ani, n_frames)
    
    # striped_color_wheel
    print('stepped_color_wheel')
    ani.generator = generators.striped_color_wheel()
    play(ani, n_frames)
    print('stepped_color_wheel(stripe_size=1)')
    ani.generator = generators.striped_color_wheel(stripe_size=1)
    play(ani, n_frames)
    
    #fading_color_wheel
    print('fading_color_wheel(mode=FADE_OUT) (default)')
    ani.generator = generators.fading_color_wheel()
    play(ani, n_frames)
    print('fading_color_wheel(mode=FADE_IN)')
    ani.generator = generators.fading_color_wheel(mode=trickLED.FADE_IN)
    play(ani, n_frames)
    print('fading_color_wheel(mode=FADE_IN_OUT)')
    ani.generator = generators.fading_color_wheel(mode=trickLED.FADE_IN_OUT)
    play(ani, n_frames)
    
    # color_compliment
    print('color_compliment()')
    ani.generator = generators.color_compliment(stripe_size=10)
    play(ani, n_frames)
    
    # random_vivid
    print('random_vivid()')
    ani.generator = generators.random_vivid()
    play(ani, n_frames)
    
    # random_pastel
    print('random_pastel()')
    ani.generator = generators.random_pastel()
    play(ani, n_frames)
    print('random_pastel(mask=(127, 0, 31))')
    ani.generator = generators.random_pastel(mask=(127, 0, 31))
    play(ani, n_frames)
    print('random_pastel(mask=(0, 63, 63))')
    ani.generator = generators.random_pastel(mask=(0, 63, 63))
    play(ani, n_frames)

def sock_stream_handler(data):


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('', 5580))
    sock.listen(5)
    while True:
        cxn, addr = sock.accept()
        print('Connection from {}'.format(addr))
        cxn.send(b'Welcome')


if __name__ == '__main__':
    if sys.platform == 'esp32':
        led_pin = machine.Pin(26)
    else:
        # labeled D2 on most ESP8266 boards
        led_pin = machine.Pin(4)

    sta = connect(settings.SSID, settings.WIFI_PWD)
    tl = trickLED.TrickLED(led_pin, 60)
    """
    while True:
        demo_animations(tl, 150)
        demo_generators(tl, 150)
    """