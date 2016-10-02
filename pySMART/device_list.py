#Copyright (C) 2014 Marc Herndon
#
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License,
#version 2, as published by the Free Software Foundation.
#
#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
This module contains the definition of the `DeviceList` class, used to
represent all physical storage devices connected to the system.
Once initialized, the sole member `devices` will contain a list of `Device`
objects.

This class has no public methods.  All interaction should be through the
`Device` class API.
"""
# Python built-ins
from subprocess import Popen, PIPE

# pySMART module imports
from .device import Device
from .utils import OS, rescan_device_busses

class DeviceList(object):
    """
    Represents a list of all the storage devices connected to this computer.
    """
    def __init__(self, init=True, dofulldevicescan=True):
        """
        Instantiates and optionally initializes the `DeviceList`.

        ###Args:
        * **init (bool):** By default, `pySMART.device_list.DeviceList.devices`
        is populated with `Device` objects during instantiation. Setting init to
        False will skip initialization and create an empty
        `pySMART.device_list.DeviceList` object instead.
        """
        self.devices = []
        """
        **(list of `Device`):** Contains all storage devices detected during
        instantiation, as `Device` objects.
        """
        self.simpledevicelist = []
        """
        **(list of dict):** Contains a list of storage devices detected during
        instantiation, by name and interface. This is meant to be used for
        better GUI integration (ie. calling Device() manually, one by one).
        """
        if init:
            self._initialize(dofulldevicescan)

    def __repr__(self):
        """Define a basic representation of the class object."""
        rep = "<DeviceList contents:\n"
        for device in self.devices:
            rep += str(device) + '\n'
        return rep + '>'
        #return "<DeviceList contents:%r>" % (self.devices)

    def _cleanup(self):
        """
        Removes duplicate ATA devices that correspond to an existing CSMI
        device. Also removes any device with no capacity value, as this
        indicates removable storage, ie: CD/DVD-ROM, ZIP, etc.
        """
        # We can't operate directly on the list while we're iterating
        # over it, so we collect indeces to delete and remove them later
        to_delete = []
        # Enumerate the list to get tuples containing indeces and values
        for index, device in enumerate(self.devices):
            if device.interface == 'csmi':
                for otherindex, otherdevice in enumerate(self.devices):
                    if (otherdevice.interface == 'ata' or
                            otherdevice.interface == 'sata'):
                        if device.serial == otherdevice.serial:
                            to_delete.append(otherindex)
                            device._sd_name = otherdevice.name
            if device.capacity == None and index not in to_delete:
                to_delete.append(index)
        # Recreate the self.devices list without the marked indeces
        self.devices[:] = [v for i, v in enumerate(self.devices)
                           if i not in to_delete]

    def _initialize(self, dofulldevicescan=True):
        """
        Scans system busses for attached devices and add them to the
        `DeviceList` as `Device` objects.
        """
        # On Windows machines we should re-initialize the system busses
        # before scanning for disks; coincidentally this wakes up all
        # USB storage devices as well and can take some time.
        #
        # XXX The rescan_* and following Popen call take 3 seconds on Windows
        # when lots of devices are plugged in (including USB)
        if OS == 'Windows':
            rescan_device_busses()
        cmd = Popen('smartctl --scan-open', shell=True,
                    stdout=PIPE, stderr=PIPE)
        # XXX communicate() takes another second
        _stdout, _stderr = cmd.communicate()
        _stdout = _stdout.decode('UTF-8')
        devlist = {}
        for line in _stdout.split('\n'):
            if not ('failed:' in line or line == ''):
                name = line.split(' ')[0].replace('/dev/', '')
                # CSMI devices are explicitly of the 'csmi' type and do not
                # require further disambiguation
                # Other device types will be disambiguated by Device.__init__
                interface = None
                if name[0:4] == 'csmi':
                  interface = 'csmi'
                if dofulldevicescan == True:
                  # XXX The following Device() call takes between 1.3-1.7 seconds to complete
                  self.devices.append(Device(name, interface=interface))
                self.simpledevicelist.append({ 'name': name, 'interface': interface })
        # Remove duplicates and unwanted devices (optical, etc.) from the list
        self._cleanup()
        # Sort the list alphabetically by device name
        self.simpledevicelist.sort(key=lambda name: name)
        self.devices.sort(key=lambda device: device.name)

    def list_devicenames(self):
      """
      Returns the list of devices output by --scan-open above as a dictionary
      """
      pass

__all__ = ['DeviceList']
