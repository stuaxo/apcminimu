#!/bin/python
# -*- coding: utf-8 -*-

"""
get input from a real APC mini and display it on this.

usage
-----

$ python apc_mini.py "APC MINI MIDI 1"

- The parameter is the midi device to use.


install
-------

$ pip install kivy mido

"""


import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import itertools
import sys
import threading
import traceback

import mido

from time import sleep

from kivy.app import App
from kivy.cache import Cache
from kivy.atlas import Atlas
from kivy.clock import Clock, mainthread
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button

# TODO - Other modes, control lights

# Light colours
OFF = 0
GREEN = 1
GREEN_BLINK = 1
RED = 3
RED_BLINK = 4
YELLOW = 5
YELLOW_BLINK = 6

COLOR = 1
BLINK = 2

TOGGLE = 1
GATE = 2

class APCMiniController(object):
    def __init__(self, midiport, light_behaviour=None):
        self.midiport = midiport

    def recv_midi(self, msg):
        pass

class MidiButton(Button):
    def __init__(self, note, *args, **kwargs):
        self.note = note
        self.light_color = OFF
        Button.__init__(self, *args, **kwargs)

class APCMiniWidget(GridLayout):
    """
    Widget holding all the controls on a real APC Mini.

    buttons are in a dict indexed by note
    sliders are in a dict indexed by control
    """
    def __init__(self, *args, **kwargs):
        ## BOTTOM_LABELS = [[u"▲"], [u"▼"], [u"◀"], [u"▶"], ["volume", "pan", "send", "device"], ["shift"]]
        GridLayout.__init__(self, cols=9, rows=10)   # chuck all the controls into one grid        
        self.note_buttons = {}
        self.control_sliders = {}

        scene_ids = xrange(82, 90).__iter__()
        for row in xrange(7, -1, -1):
            for col in xrange(0, 8):
                # first 8 cols are clip launchers
                note = (row * 8) + col
                self.add_widget( self.create_button("clip_launch_%d" % note, note) )

            # last column is scene launch
            note = next(scene_ids)
            self.add_widget( self.create_button("scene_launch_%d" % row, note) )

        # row 8 - control buttons and shift
        for i, note in enumerate(xrange(64, 72)):
            self.add_widget( self.create_button("control_%d" % i, note) )

        self.add_widget( self.create_button("shift", 98) )

        # row 9 - sliders
        for i, note in enumerate(xrange(48, 57)):
            self.add_widget( self.create_slider("slider_%d" % i, note) )


    def create_button(self, id, note):
        button = MidiButton(note=note, id=id, text="")
        button.bind(on_press=self.handle_press)
        button.bind(on_release=self.handle_release)
        self.note_buttons[note] = button
        return button

    def create_slider(self, id, controller):
        slider = Slider(id=id, min=0, max=127, value=63, orientation='vertical', size_hint=(1. / 9, 8))
        slider.bind(value_normalized=self.handle_slide)
        self.control_sliders[controller] = slider
        return slider

    def recv_midi(self, msg):
        """
        Change the state of a button or slider in response to midi
        """
        if msg.type in ['note_on', 'note_off']:
            print 'got midi %s' % msg
            button = self.note_buttons.get(msg.note)
            if button:
                if msg.type == 'note_on':
                    print 'set button %s %s' % (button.id, id(button))
                    button.state = 'down'
                    self.handle_press(button)
                elif msg.type == 'note_off':
                    button.state = 'normal'
                    self.handle_release(button)
                button.canvas.ask_update()
            else:
                print 'no button mapped to note {}'.format(msg.note)
        elif msg.type == 'control_change':
            slider = self.control_sliders.get(msg.control)
            if slider:
                slider.value = msg.value
                slider.canvas.ask_update()
            else:
                print 'no slider mapped to control {}'.format(msg.control)

    def handle_press(self, button):
        app = App.get_running_app()
        if app.light_behaviour == GATE:
            button.light_color = YELLOW
            m = mido.Message('note_on', note=button.note, velocity=button.light_color)
            app.midiport.send(m)
        elif app.light_behaviour == TOGGLE:
            if button.light_color is OFF:
                button.light_color = YELLOW
            else:
                button.light_color = OFF
            m = mido.Message('note_on', note=button.note, velocity=button.light_color)
            app.midiport.send(m)

    def handle_release(self, button):
        app = App.get_running_app()
        if app.light_behaviour == GATE:
            m = mido.Message('note_on', note=button.note, velocity=OFF)
            app.midiport.send(m)


    def handle_slide(self, slider, *args, **kwargs):
        print 'slide %s %d' % (slider.id, slider.value)




class ApcMiniApp(App):
    CLIP_LAUNCH_NOTES = xrange(0, 64)

    note_buttons = {}
    control_sliders = {}

    def __init__(self, channel=0, light_behaviour=None, *args, **kwargs):
        App.__init__(self, *args, **kwargs)
        self.channel = channel
        self.input_port = 'blah blah'
        self.output_port = 'blah blah out'
        self.apc_widget = None
        self.midiport = None
        self.light_behaviour = light_behaviour
    
#    def build(self):
#        #d = "kivy-themes/red-lightgrey"
#        #atlas = Atlas(d + "/button_images/button_images.atlas")
#        atlas = "kivy-themes/red-lightgrey/defaulttheme.atlas"
#        #Cache.append("kv.atlas", 'data/images/defaulttheme', atlas)

    def open_input(self, portname):
        if self.midiport:
            self.midiport.close()
        self.midiport = mido.open_ioport(portname, callback=self.recv_midi, autoreset=True)
        print 'CONNECTED TO: %s' % self.midiport.name
        # sysex to set APC Mini to mode 1
        ##m = mido.Message('sysex', data=bytearray(b'\x47\x7F\x28\x60\x00\x04\x41\x09\x01\x04'))
        ##self.midiport.send(m)

    def light_matrix(self, x, y, color):
        pass

    def get_apc_widget(self):
        """
        Search widget tree for APCMiniWidget
        """
        if self.apc_widget is None and self.root:
            for widget in self.root.walk():
                if isinstance(widget, APCMiniWidget):
                    self.apc_widget = widget
                    self.apc_widget.midiport = self.midiport ###
                    break

        return self.apc_widget


    # @mainthread
    def recv_midi(self, msg):
        global logger
        try:
            apc_widget = self.get_apc_widget()
            if not apc_widget:
                return

            if msg.channel == self.channel:
                apc_widget.recv_midi(msg)
            else:
                print 'midi msg channel {} not channel {}'.format(msg.channel, self.channel)
        except Exception as e:
            logger.exception(e)



def main():
    global app
    if len(sys.argv) > 1:
        portname = sys.argv[1]
    else:
        try:
            portname = next(name for name in mido.get_ioport_names() if name.startswith('APC MINI MIDI'))
        except StopIteration:
            portname = None   # Use default port


    app = ApcMiniApp(light_behaviour=TOGGLE)
    app.open_input(portname)
    app.run()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        logger.exception(e)
    

