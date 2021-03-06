
#!/usr/bin/env python
#
# scopes.py
#
# This code choses the commands to send
#
# Author P G Jones - 28/05/2013 <p.g.jones@qmul.ac.uk> : First revision
#        Ed Leming - 7/04/2015 <e.leming09@googlemail.com>: Adding some further functions
#################################################################################################### 
import re
import numpy
import time

class Tektronix(object):
    """ Base class for tektronix scopes."""
    _preamble_fields = {'BYT_NR' : int, # data width for waveform
                        'BIT_NR' : int, # number of bits per waveform point
                        'ENCDG'  : str, # encoding of waveform (binary/ascii)
                        'BN_FMT' : str, # binary format of waveform
                        'BYT_OR' : str, # ordering of waveform data bytes (LSB/MSB)
                        'NR_PT'  : int, # record length of record waveform
                        'PT_FMT' : str, # Point format (Y/ENV)
                        'XUNIT'  : str, # X unit 
                        'XINCR'  : float, # Difference between two x points
                        'XZERO'  : float, # X zero value
                        'PT_OFF' : int, # Ignored?
                        'YUNIT'  : str, # Y unit
                        'YMULT'  : float, # Difference between two y point
                        'YOFF'   : float, # Y offset
                        'YZERO'  : float, # Y zero value
                        'RECORDLENGTH' : int } # Number of data points
    def __init__(self, connection):
        """ Initialise the scope with a connection to the scope."""
        # Initiliase setttings to nothing
        self._preamble = {}
        self._channels = {} 
        self._connection = connection
        self._connection.send_sync("*rst") # Reset the scope
        self._connection.send_sync("lock none") # Unlock the front panel
        self._connection.send_sync("*cls") # Clear the scope
        self._connection.send_sync("verbose 1") # If the headers are on ensure they are verbose
        self._locked = False # Local locking of scope settings
        self._data_start = 1
        self._triggered = False
    def __del__(self):
        """ Free up the scope."""
        self.unlock()
#################################################################################################### 
    def interactive(self):
        """ Control the scope interactively."""
        if self._locked:
            raise Exception("Scope is locked.")
        print "Enter: Interactive mode."
        try:
            while True:
                command = raw_input("COMMAND: ")
                if command[-1] == "?":
                    print self._connection.ask(command), "\n"
                else:
                    self._connection.send_sync(command)
        except KeyboardInterrupt:
            print "Exit: Interative mode."
    def get_active_channels(self):
        """ Return the number of active channels."""
        if not self._locked:
            self._find_active_channels()
        return self._channels
    def lock(self):
        """ Get the current settings and allow no more changes."""
        self._connection.send_sync("lock all") # Prevent people channing the settings via the front panel
        self._connection.send_sync("header off") # Turn all headers off
        self._locked = True
    def begin(self):
        """ Start taking data."""
        if self._locked is False:
            print "Not locked"
            raise
        time.sleep(5) # Prudent to wait for the scope to recover from the settings...
        self._find_active_channels()
        for channel in self._channels.keys():
            if self._channels[channel]:
                self._get_preamble(channel)
        self._connection.send_sync("message:show 'Taking Data, scope is locked.'")
        self._connection.send_sync("message:state on")
        self._connection.send_sync("message:box 650 100")
    def unlock(self):
        """ Unlock and allow changes."""
        self._locked = False
        self._connection.send_sync("message:state off")
        self._connection.send_sync("lock none") # Allow the front panel to be used
    def get_preamble(self, channel):
        return self._preamble[channel]
#### Display Settings ###############################################################################
    def set_display_y(self, channel, mult, pos=0.0, offset=0.0):
        """ The channel y display settings, these do not affect the waveform.
        mult or volts per div, yoffset (in volts) and position in divs."""
        self._connection.send_sync("ch%i:volts %e" %(channel, mult))
        self._connection.send_sync("ch%i:position %e" %(channel, pos))
        self._connection.send_sync("ch%i:offset %e" %(channel, offset))
#### Waveform Settings ##############################################################################
    def set_record_length(self, length):
        self._connection.send_sync("horizontal:recordlength %e" % (length))
    def get_record_length(self):
        #rtn_str = self._connection.send_sync("horizontal:recordlength?") #3000 model
        rtn_str = self._connection.send_sync("wfmoutpre:recordlength?") #2000 model 
        print rtn_str
        return [int(s) for s in rtn_str.split() if s.isdigit()][0]
    def set_data_mode(self, data_start=1, data_stop=None):
        """ Set the settings for the data returned by the scope."""
        self._connection.send_sync("wfmoutpre:pt_fmt y") # Single point format
        self._connection.send_sync("data:encdg ribinary") # Signed int binary mode
        self._connection.send_sync("data:start %i" % data_start) # Start point
        self._data_start = data_start
        if data_stop is None:
            data_stop = int(self._connection.ask("horizontal:acqlength?"))
        self._connection.send_sync("data:stop %i" % data_stop) # 100000 is full 
#### Cursor Settings ################################################################################
    def set_cursors(self, low, high):
        self._connection.send_sync("cursor:function waveform")
        self._connection.send_sync("cursor:vbars:position1 %e" % low)
        self._connection.send_sync("cursor:vbars:position2 %e" % high)
#### Horizontal Settings ############################################################################
    def set_horizontal_scale(self, scale):
        """ Sets the timebase horizontal scale in seconds per div."""
        self._connection.send_sync("horizontal:scale %e" % scale)
    def set_horizontal_delay(self, delay):
        """Sets the horizontal delay time (position) that is used
        when delay is on (the default mode)."""
        self._connection.send_sync("horizontal:delay:mode on") #for clarity
        self._connection.send_sync("horizontal:delay:time %e" % (delay))
    def set_sample_rate(self, rate):
        """Sets the digitizer sample rate"""
        self._connection.send_sync("horizontal:samplerate %e" % (rate))
#### Channel Settings ###############################################################################
    def set_channel_y(self, channel, scale, pos=0.0, offset=0.0):
        self._connection.send_sync("ch%i:scale %e" % (channel, scale))
        self._connection.send_sync("ch%i:position %e" %(channel, pos))
        self._connection.send_sync("ch%i:offset %e" %(channel, offset))
    def set_active_channel(self, channel, active=True):
        if active:
            self._connection.send_sync("select:ch%i on" % channel)
        else:
            self._connection.send_sync("select:ch%i off" % channel)
    def set_channel_termination(self, channel, resistance):
        """Set the channel terminaltion, options are 50, 75 or 1e6 ohms"""
        self._connection.send_sync("ch%i:termination %e" % (channel, resistance))
    def set_invert_channel(self, channel, invert=True):
        """ Invert the channel."""
        if invert:
            self._connection.send_sync("ch%i:invert on" % channel)
        else:
            self._connection.send_sync("ch%i:invert off" % channel)
    def set_channel_coupling(self, channel, coupling="ac"):
        self._connection.send_sync("ch%i:coupling %s" % (channel, coupling))
    def set_probe_gain(self, channel, gain):
        self._connection.send_sync("ch%i:probe:gain %f" % (channel, gain))
#### Acquisition Type ###############################################################################
    def set_single_acquisition(self):
        """ Set the scope in single acquisition mode."""
        self._connection.send_sync("acquire:mode sample") # Single acquisition mode, not average
    def set_average_acquisition(self, averages):
        """ Set the scope in average acquisition mode."""
        self._connection.send_sync("acquire:mode average")
        self._connection.send_sync("acquire::numavg %i" % averages)
#### Measurement Type ###############################################################################
    def set_measurement(self, type):
        """ Set the scope to do a measurement of the waveform."""
        if not type in ["area"]:
            print "Unknown measurement."
            return
        self._connection.send_sync("measurement:immed:type %s" % type)
        self._connection.send_sync("measurement:gating cursor")
        #self._connection.send_sync("measurement:immed:state on" % measurement)
#### Trigger Settings ###############################################################################
    def set_untriggered(self):
        """ Set the scope to untriggered mode."""
        self._triggered = False
        self._connection.send_sync("trigger:a:mode auto")
    def set_edge_trigger(self, trigger_level, channel, falling=False):
        """ Set an edge trigger with the settings."""
        self._triggered = True
        self._connection.send_sync("trigger:a:type edge") # Chose the edge trigger
        self._connection.send_sync("trigger:a:mode normal") # Normal mode (waits for a trigger)
        self._connection.send_sync("trigger:a:edge:source ch%i" % channel)
        self._connection.send_sync("trigger:a:edge:coupling dc") # DC coupling
        if falling:
            self._connection.send_sync("trigger:a:edge:slope fall") # Falling or ...
        else:
            self._connection.send_sync("trigger:a:edge:slope rise") # ... rising slope
        self._connection.send_sync("trigger:a:level %e" % trigger_level) # Sets the trigger level in Volts
        self._connection.send_sync("trigger:a:level:ch%i %e" % (channel, trigger_level)) # Sets the trigger level in Volts
#### Data acquistion ################################################################################
    def get_trigger_frequency(self):
        trigger_frequency = self._connection.ask("trigger:frequency?")
        if trigger_frequency == "9.0e+37": # NaN - weird value from scope
            return 0.0
        elif trigger_frequency is not None:
            return float(trigger_frequency)
    def acquire(self):
        """ Wait until scope has an acquisition."""
        self._connection.send("acquire:state run") # Equivalent to on
        # Wait until acquiring and there is a trigger
        while True:
            acquisition_state = self._connection.ask("acquire:state?")
            if acquisition_state is not None and int(acquisition_state) != 0: # acquired a trigger
                if self._triggered and self._connection.ask("trigger:state?") != "READY": # Triggered as well 
                    break
                elif not self._triggered:
                    break
                # Otherwise carry on
    def acquire_time_check(self, timeout=0.3):
        """ Wait until scope has an acquisition and optionally has triggered."""
        self._connection.send("acquire:state run") # Equivalent to on
        # Wait until acquiring and there is a trigger
        time_start = time.time()
        while int(self._connection.ask("acquire:state?")) == 0 or (self._connection.ask("trigger:state?") != "TRIGGER"):
            #print self._connection.ask("acquire:state?"), self._connection.ask("trigger:state?"), time.time() - time_start
            if (time.time() - time_start) > timeout:
                return False
            time.sleep(0.05)
        return True
    def get_waveform(self, channel):
        """ Acquire a waveform from channel=channel."""
        #if self._locked == False or self._channels[channel] == False:
        #    raise Exception("Not locked or channel not active.")
        self._connection.send("data:source ch%i" % channel) # Set the data source to the channel
        data, count = None, 0
        while data == None:
            self._connection.ask("*opc?") # Wait until scope is ready
            data = self._connection.ask("curve?")
            if count > 5:
                raise Exception("Scope has errored.")
        header_len = 2 + int(data[1])
        waveform = numpy.fromstring(data[header_len:], self._get_data_type(channel))
        # Now convert the waveform into voltage units
        waveform = self._preamble[channel]['YZERO'] + (waveform - self._preamble[channel]['YOFF']) * self._preamble[channel]['YMULT']
        return waveform
    def get_timeform(self, channel):
        """ Return the timebase for the waveform."""
        # Now build the relevant timing array correcting for data portion acquired
        timeform = self._preamble[channel]['XZERO'] + self._data_start * self._preamble[channel]['XINCR'] + \
            (numpy.arange(self._preamble[channel]['NR_PT']) - self._preamble[channel]['PT_OFF']) * self._preamble[channel]['XINCR']
        return timeform
    def get_measurement(self, channel):
        """ Return the measurement value."""
        self._connection.send_sync("measurement:immed:source1 ch%i" % channel)
        value = self._connection.ask("measurement:immed:value?")
        if value == "2.8740E-06":
            return None
        elif value is not None:
            return float(value)
#### Internal ###################################################################################### 
    def _find_active_channels(self):
        """ Finds out how many channels are active."""
        self._connection.send("header on")
        for select in self._connection.ask("select?").strip()[8:].split(';'):
            channel_info = re.match("CH(\d) (\d)", select)
            if channel_info is not None:
                channel = int(channel_info.groups()[0])
                state = channel_info.groups()[1]  == '1'
                self._channels[channel] = state
        self._connection.send("header off")
    def _get_preamble(self, channel):
        """ Retrieve the preamble from the scope."""
        self._connection.send_sync("data:source ch%i" % channel) # Set the data source to the channel
        self._connection.send_sync("header on") # Turn headers on
        preamble, pr = {}, None
        while pr == None:
            pr = self._connection.ask("wfmoutpre?")
        for preamble_setting in pr.strip()[len("wfmoutpre:") + 1:].split(';'): # Ask for waveform information
            key, value = preamble_setting.split(' ',1)
            if key in Tektronix._preamble_fields.keys():
                preamble[key] = Tektronix._preamble_fields[key](value) # Conver the value to the correct field type 
            else:
                print "Preamble key", key, "is ignored."
        self._preamble[channel] = preamble
        self._connection.send_sync("header off") # Turn the headers offf
    def _get_data_type(self, channel):
        """ Return the data type for the given channel."""
        data_type = ""
        if self._preamble[channel]['BYT_OR'] == 'MSB': # Endeaness
            data_type = '>'
        else:
            data_type = '<'
        if self._preamble[channel]['BN_FMT'] == 'RI': # Signed or unsigned
            data_type += 'i'
        else:
            data_type += 'u'
        data_type += str(self._preamble[channel]['BYT_NR']) # Number of bits per data point
        return data_type
                        
class Tektronix2000(Tektronix):
    """ Specific commands for the DPO/MSO 2000 series scopes."""
    # Update the preamble fields with those specific to this scope model                    
    Tektronix._preamble_fields.update( { 'WFID'   : str, # Description of the data
                                         'VSCALE' : float, 
                                         'HSCALE' : float, 
                                         'VPOS'   : float,
                                         'VOFFSET': float,
                                         'HDELAY' : float,
                                         'COMPOSITION': str,
                                         'FILTERFREQ' : int } )
    def __init__(self, connection):
        """ Intialise the scope with a connection."""
        super(Tektronix2000, self).__init__(connection)

class Tektronix3000(Tektronix):
    """ Specific commands for the DPO/MSO 2000 series scopes."""
    # Update the preamble fields with those specific to this scope model                    
    Tektronix._preamble_fields.update( { 'CENTERFREQUENCY' : float,
                                         'DOMAIN'          : str, 
                                         'REFLEVEL'        : float,
                                         'SPAN'            : float,
                                         'WFMTYPE'         : str } )
    def __init__(self, connection):
        """ Intialise the scope with a connection."""
        super(Tektronix3000, self).__init__(connection)
