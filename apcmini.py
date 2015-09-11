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


import itertools
import threading
import sys

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
AMBER = 5
AMBER_BLINK = 6

COLOR = 1
BLINK = 2


class APCWidget(GridLayout):
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
        button = Button(id=id, text="")
        button.bind(on_press=self.handle_press)
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
            button = self.note_buttons.get(msg.note)
            if button:
                if msg.type == 'note_on':
                    print 'set button %s %s' % (button.id, id(button))
                    button.state = 'down'
                elif msg.type == 'note_off':
                    button.state = 'normal'
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
        print 'press %s %s' % (button.id, id(button))

    def handle_slide(self, slider, *args, **kwargs):
        print 'slide %s %d' % (slider.id, slider.value)




class ApcMiniApp(App):
    CLIP_LAUNCH_NOTES = xrange(0, 64)

    note_buttons = {}
    control_sliders = {}

    def __init__(self, channel = 0, *args, **kwargs):
        App.__init__(self, *args, **kwargs)
        self.channel = channel
        self.input_port = 'blah blah'
        self.output_port = 'blah blah out'
        self.apc_widget = None
        self.midiport = None
    
    def build(self):
        #d = "kivy-themes/red-lightgrey"
        #atlas = Atlas(d + "/button_images/button_images.atlas")
        atlas = "kivy-themes/red-lightgrey/defaulttheme.atlas"
        #Cache.append("kv.atlas", 'data/images/defaulttheme', atlas)

    def open_input(self, portname):
        if self.midiport:
            self.midiport.close()
        self.midiport = mido.open_input(portname, callback=self.recv_midi)

    def light_matrix(x, y, color):
        pass

    # @mainthread
    def recv_midi(self, msg):
        try:
            if self.apc_widget is None:
                for widget in self.root.walk():
                    if isinstance(widget, APCWidget):
                        print 'Found APC Widget'
                        self.apc_widget = widget
                        break
                else:
                    print 'No APC Widget'
                    return

            if msg.channel == self.channel:
                self.apc_widget.recv_midi(msg)
            else:
                print 'midi msg channel {} not channel {}'.format(msg.channel, self.channel)
        except Exception as e:
            print e



def main():
    global app
    if len(sys.argv) > 1:
        portname = sys.argv[1]
    else:
        portname = None   # Use default port

    print portname
    app = ApcMiniApp()
    app.open_input(portname)
    app.run()

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print e
    

