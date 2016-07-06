#!/usr/bin/env python
"""
mbed SDK
Copyright (c) 2011-2016 ARM Limited

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from conn_primitive import ConnectorPrimitive


class RemoteConnectorPrimitive(ConnectorPrimitive):
    def __init__(self, name, config):
        ConnectorPrimitive.__init__(self, name)
        self.config = config
        self.target_id = self.config.get('target_id', None)
        self.grm_host = config.get('grm_host', None)
        self.grm_port = int(config.get('grm_port', 8000))
        self.grm_module = config.get('grm_module', 'unknown')
        self.platform_name = config.get('platform_name', None)
        self.baudrate = config.get('baudrate', 115200)
        self.image_path = config.get('image_path', None)

        # Global Resource Mgr tool-kit
        self.remote_module = None
        self.selected_resource = None
        self.client = None

        # Initialize remote resource manager
        self.__remote_init()

    def __remote_init(self):
        """! Initialize DUT using GRM APIs """

        # We want to load global resource manager module by name from command line (switch --grm)
        try:
            self.remote_module = __import__(self.grm_module)
        except ImportError as e:
            self.logger.prn_err("unable to load global resource manager '%s' module!"% self.grm_module)
            self.remote_module = None
            return

        self.logger.prn_inf("remote resources initialization: remote(host=%s, port=%s)"% (self.grm_host, self.grm_port))

        # Connect to remote global resource manager
        self.client = self.remote_module.RaasClient(host=self.grm_host, port=self.grm_port)

        # First get the resources
        resources = self.client.get_resources()
        self.logger.prn_inf("remote resources count: %d" % len(resources))

        # Query for available resource
        # Automatic selection and allocation of a resource
        self.selected_resource = self.client.allocate({
                "platform_name": self.platform_name
        })

        # Open remote connection to DUT
        serial_parameters = self.remote_module.SerialParameters(lineMode=False, baudrate=self.baudrate)
        self.selected_resource.openConnection(parameters=serial_parameters)
        # Remote DUT reset
        self.__remote_flashing(self.image_path)
        self.__remote_reset()

    def __remote_reset(self):
        """! Use GRM remote API to reset DUT """
        self.logger.prn_inf("remote resources reset...")
        if not self.selected_resource.reset():
            self.logger.prn_err("remote resources reset failed!")

    def __remote_flashing(self, filename):
        """! Use GRM remote API to flash DUT """
        self.logger.prn_inf("remote resources flashing with '%s'..."% filename)
        if not self.selected_resource.flash(filename, forceflash=True):
            self.logger.prn_err("remote resources flashing failed!")

    def read(self, count):
        """! Read 'count' bytes of data from DUT """
        data = self.selected_resource.read(count)
        return data

    def write(self, payload, log=False):
        """! Write 'payload' to DUT """
        if self.selected_resource:
            self.selected_resource.writeline(payload)
            if log:
                self.logger.prn_txd(payload)
        return payload

    def flush(self):
        pass

    def connected(self):
        return all([self.self.remote_module,
            self.selected_resource,
            self.selected_resource.is_connected])

    def error(self):
        return self.LAST_ERROR

    def finish(self):
        # Finally once we're done with the resource
        # we disconnect and release the allocation
        if self.selected_resource:
            if self.selected_resource.is_connected:
                self.selected_resource.closeConnection()
            if self.selected_resource.is_allocated:
                self.selected_resource.release()

    def __del__(self):
        self.finish()
